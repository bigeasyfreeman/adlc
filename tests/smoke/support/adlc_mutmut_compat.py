#!/usr/bin/env python3
from __future__ import annotations

import inspect
import multiprocessing as mp
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_original_set_start_method = mp.set_start_method


def _safe_set_start_method(method=None, *args, **kwargs):
    try:
        return _original_set_start_method(method, *args, **kwargs)
    except RuntimeError as exc:
        if "context has already been set" not in str(exc):
            raise
        current = None
        try:
            current = mp.get_start_method(allow_none=True)
        except Exception:
            pass
        if method is None or current == method:
            return None
        raise


mp.set_start_method = _safe_set_start_method

import mutmut.__main__ as mutmut_main

_original_strip_prefix = mutmut_main.strip_prefix


def _patched_strip_prefix(value, *, prefix, strict=False):
    if prefix == "src.":
        return value
    return _original_strip_prefix(value, prefix=prefix, strict=strict)


def _patched_record_trampoline_hit(name):
    config = getattr(mutmut_main.mutmut, "config", None)
    max_stack_depth = getattr(config, "max_stack_depth", -1)
    if max_stack_depth != -1:
        frame = inspect.currentframe()
        depth = max_stack_depth
        while depth and frame:
            if "pytest" in frame.f_code.co_filename or "hammett" in frame.f_code.co_filename:
                break
            frame = frame.f_back
            depth -= 1
        if not depth:
            return
    mutmut_main.mutmut._stats.add(name)


mutmut_main.strip_prefix = _patched_strip_prefix
mutmut_main.record_trampoline_hit = _patched_record_trampoline_hit


def _prepare_mutation_workspace(max_children: int) -> mutmut_main.PytestRunner:
    os.environ["MUTANT_UNDER_TEST"] = "mutant_generation"
    mutmut_main.ensure_config_loaded()

    start = datetime.now()
    mutmut_main.makedirs(Path("mutants"), exist_ok=True)
    with mutmut_main.CatchOutput(spinner_title="Generating mutants"):
        mutmut_main.copy_src_dir()
        mutmut_main.create_mutants(max_children)
        mutmut_main.copy_also_copy_files()

    elapsed = datetime.now() - start
    print(f"    done in {round(elapsed.total_seconds() * 1000)}ms")

    for path in (Path("."), Path("src"), Path("source")):
        mutated_path = Path("mutants") / path
        if mutated_path.exists():
            sys.path.insert(0, str(mutated_path.absolute()))

    for path in (Path("."), Path("src"), Path("source")):
        for index in range(len(sys.path)):
            while index < len(sys.path) and Path(sys.path[index]).resolve() == path.resolve():
                del sys.path[index]

    runner = mutmut_main.PytestRunner()
    runner.prepare_main_test_run()
    return runner


def _run_clean_suite(runner, mutant_names) -> None:
    os.environ["MUTANT_UNDER_TEST"] = ""
    with mutmut_main.CatchOutput(spinner_title="Running clean tests") as output_catcher:
        tests = mutmut_main.tests_for_mutant_names(mutant_names)
        clean_exit_code = runner.run_tests(mutant_name=None, tests=tests)
        if clean_exit_code != 0:
            output_catcher.dump_output()
            print("Failed to run clean test")
            raise SystemExit(1)
    print("    done")


def _run_mutants(mutants, source_file_mutation_data_by_path) -> int:
    start = datetime.now()
    count_tried = 0

    print("Running mutation testing")
    for mutation_data, mutant_name, _ in mutants:
        mutmut_main.print_stats(source_file_mutation_data_by_path)

        mutant_name = mutant_name.replace("__init__.", "")
        tests = sorted(
            mutmut_main.mutmut.tests_by_mangled_function_name.get(
                mutmut_main.mangled_name_from_mutant_name(mutant_name),
                [],
            ),
            key=lambda test_name: mutmut_main.mutmut.duration_by_test[test_name],
        )

        if not tests:
            mutation_data.exit_code_by_key[mutant_name] = 33
            mutation_data.save()
            count_tried += 1
            continue

        env = os.environ.copy()
        env["MUTANT_UNDER_TEST"] = mutant_name
        env["PY_IGNORE_IMPORTMISMATCH"] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", *tests],
            cwd="mutants",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        mutation_data.exit_code_by_key[mutant_name] = result.returncode
        mutation_data.save()
        count_tried += 1

    elapsed = max((datetime.now() - start).total_seconds(), 0.001)
    mutmut_main.print_stats(source_file_mutation_data_by_path, force_output=True)
    print()
    print(f"{count_tried / elapsed:.2f} mutations/second")
    return 0


def command_run(mutant_names) -> int:
    runner = _prepare_mutation_workspace(max_children=1)
    mutmut_main.collect_or_load_stats(runner)
    mutants, source_file_mutation_data_by_path = mutmut_main.collect_source_file_mutation_data(
        mutant_names=mutant_names
    )
    _run_clean_suite(runner, mutant_names)
    mutmut_main.run_forced_fail_test(runner)
    return _run_mutants(mutants, source_file_mutation_data_by_path)


def command_results(show_all: bool) -> int:
    mutmut_main.ensure_config_loaded()
    for path in mutmut_main.walk_source_files():
        if not str(path).endswith(".py"):
            continue
        mutation_data = mutmut_main.SourceFileMutationData(path=path)
        mutation_data.load()
        for mutant_name, exit_code in mutation_data.exit_code_by_key.items():
            status = mutmut_main.status_by_exit_code[exit_code]
            if status == "killed" and not show_all:
                continue
            print(f"    {mutant_name}: {status}")
    return 0


def command_show(mutant_name: str) -> int:
    mutmut_main.ensure_config_loaded()
    print(mutmut_main.get_diff_for_mutant(mutant_name))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        print("Usage: python -m adlc_mutmut_compat <run|results|show> [args...]")
        return 0

    command = argv[1]
    if command == "run":
        return command_run(tuple(argv[2:]))
    if command == "results":
        return command_results("--all" in argv[2:])
    if command == "show":
        if len(argv) != 3:
            print("Usage: python -m adlc_mutmut_compat show <mutant_name>", file=sys.stderr)
            return 64
        return command_show(argv[2])

    print(f"Unknown command: {command}", file=sys.stderr)
    return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
