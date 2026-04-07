# Skill: Figma Integration

> Pulls design specs, component inventories, and screen states from Figma into the PRD and Build Brief pipeline. Validates that PRD screen specifications match actual Figma mocks. Extracts design tokens, spacing, and component names so coding agents produce pixel-accurate implementations.

---

## Why This Exists

PRDs describe screens in text. Figma has the actual designs. Without this skill:
- PRD field-detail tables drift from what design actually built
- Engineers build from text specs that are stale within a week
- Coding agents generate UI that doesn't match the mocks
- Design review becomes a rework cycle instead of a confirmation

This skill bridges the gap: it reads Figma programmatically and feeds design truth into the pipeline.

---

## Trigger

| When | What |
|------|------|
| PRD Agent Phase 5 (Screen Specs) | Pull frame names, component lists, and states from linked Figma file |
| Build Brief Phase 0 (Research) | Validate PRD screen specs against current Figma state |
| Architecture Scaffolding | Extract component names, design tokens, and layout structure for frontend stubs |
| Codegen Context Assembly | Inline design specs (spacing, colors, component hierarchy) into frontend task prompts |

---

## Input

```json
{
  "figma_file_url": "string (Figma file or frame URL)",
  "figma_access_token": "string (via MCP server auth)",
  "prd_screens": [
    {
      "screen_name": "string",
      "figma_frame_ref": "string (frame name or node ID from PRD)",
      "field_detail_table": {}
    }
  ],
  "mode": "extract | validate | design_tokens | component_inventory"
}
```

---

## Behavior

### Mode: `extract` — Pull Design Into PRD

For each Figma frame referenced in the PRD:

1. **Fetch frame metadata** via Figma API (`GET /v1/files/:file_key/nodes?ids=:node_ids`)
2. **Extract component hierarchy** — what components are used, their names, nesting
3. **Extract text content** — every text node with its content (button labels, headings, placeholder text)
4. **Extract interactive elements** — buttons, inputs, dropdowns, toggles with their states
5. **Extract screen states** — if the frame has variants (empty, filled, error, loading), list them
6. **Generate a field-detail table** from the extracted elements

**Output:**
```json
{
  "screen_name": "Invite Modal",
  "figma_frame": "Invite - Filled",
  "figma_url": "https://figma.com/file/...",
  "last_modified": "ISO date",
  "components_used": [
    {"name": "SearchableMultiSelect", "type": "input", "library": "DesignSystem/Inputs"},
    {"name": "UserChip", "type": "display", "library": "DesignSystem/Chips"},
    {"name": "PrimaryButton", "type": "button", "label": "Send"}
  ],
  "text_content": [
    {"node": "Modal Title", "content": "Share [Deliverable Name]"},
    {"node": "CTA Button", "content": "Send"},
    {"node": "Secondary Action", "content": "Copy link"}
  ],
  "states": ["empty", "filled", "sending", "sent"],
  "extracted_field_table": {
    "Modal Title": "Share [Deliverable Name]",
    "Recipient Input": "SearchableMultiSelect — org users and WRITER seat holders",
    "Chip Display": "UserChip — avatar + name + email, removable",
    "Primary CTA": "PrimaryButton — 'Send', triggers email dispatch",
    "Secondary Action": "Copy link (present in design)"
  }
}
```

### Mode: `validate` — Check PRD Against Figma

Compare every PRD screen spec against its linked Figma frame:

| PRD Says | Figma Shows | Status |
|----------|------------|--------|
| "Share" button with share/arrow icon | Frame has ShareIcon + "Share" label | ✅ Match |
| Copy link option (TBD for v1) | "Copy link" text node present in frame | ⚠️ Conflict — design has it, PRD says TBD |
| Modal title: "Share [Deliverable Name]" | Title text: "Share [Deliverable Name]" | ✅ Match |
| No error state specified | No error state frame exists | ⚠️ Gap — neither PRD nor design covers errors |

**Output: `validation_report`**
```json
{
  "matches": [{"field": "string", "prd_value": "string", "figma_value": "string"}],
  "conflicts": [{"field": "string", "prd_value": "string", "figma_value": "string", "recommendation": "string"}],
  "gaps_in_prd": [{"field": "string", "figma_has": "string", "recommendation": "add to PRD"}],
  "gaps_in_figma": [{"field": "string", "prd_has": "string", "recommendation": "design needed"}],
  "stale_screens": [{"screen": "string", "prd_last_updated": "date", "figma_last_modified": "date"}]
}
```

### Mode: `design_tokens` — Extract for Coding Agents

Pull design tokens for frontend implementation:
- Colors (hex values, CSS variable names if using a design system)
- Spacing (padding, margins, gaps)
- Typography (font family, size, weight, line height)
- Border radius, shadows, opacity
- Breakpoints (if responsive variants exist)

### Mode: `component_inventory` — Map to Code Components

If the repo has a component library (found via Codebase Research), map Figma components to existing code components:

| Figma Component | Code Component | Location | Match |
|----------------|---------------|----------|-------|
| PrimaryButton | `<Button variant="primary">` | `src/components/ui/Button.tsx` | ✅ Exists |
| SearchableMultiSelect | `<Combobox>` | `src/components/ui/Combobox.tsx` | ✅ Exists (different name) |
| UserChip | — | — | ❌ New component needed |

---

## MCP Server Contract

### Tool: `figma_extract`

```json
{
  "name": "figma_extract",
  "description": "Extract screen specs, components, and design tokens from Figma frames",
  "inputSchema": {
    "type": "object",
    "properties": {
      "figma_url": {
        "type": "string",
        "description": "Figma file or frame URL"
      },
      "mode": {
        "type": "string",
        "enum": ["extract", "validate", "design_tokens", "component_inventory"]
      },
      "prd_screens": {
        "type": "array",
        "description": "PRD screen specs to validate against (required for validate mode)"
      },
      "repo_path": {
        "type": "string",
        "description": "Repo path for component_inventory mode"
      }
    },
    "required": ["figma_url", "mode"]
  }
}
```

---

## CLI Interface

```bash
# Extract screen specs from Figma
adlc-figma extract --url "https://figma.com/file/..." --output ./figma-specs.json

# Validate PRD against Figma
adlc-figma validate --url "https://figma.com/file/..." --prd ./prd.md

# Extract design tokens
adlc-figma tokens --url "https://figma.com/file/..." --output ./tokens.json

# Map Figma components to code components
adlc-figma components --url "https://figma.com/file/..." --repo ./my-repo
```

---

## Quality Gates

- [ ] Every PRD screen with a Figma reference has been validated
- [ ] Conflicts between PRD and Figma are flagged with recommendations
- [ ] Component inventory maps Figma components to code (or flags new ones needed)
- [ ] Design tokens are extracted in a format coding agents can consume (CSS variables or JSON)
- [ ] Stale screens (Figma updated after PRD was written) are flagged
