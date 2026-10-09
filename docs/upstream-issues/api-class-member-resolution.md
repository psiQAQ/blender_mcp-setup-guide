# Issue title

get_python_api_docs cannot resolve bpy.types.Object.location without a duplicated class name

## Issue body

### Environment

Reproduced on Windows x64 on 2026-10-10 with the **unmodified official `mcp` Extension and an independent uv-installed `blender-mcp` stdio server**, using three fresh GUI sessions per version. No integrated Extension or `_vendor` was installed; installed official source hashes match the fixed Git trees.

| Blender / bundled Python | Upstream commit | Extension / server | Standard member lookup |
| --- | --- | --- | --- |
| 5.1.1 / 3.13.9 | v1.0.3, `2cea8d566dde07fbac28a61d698909d69724e853` | 1.0.3 / 1.0.3 | Failed 3/3 |
| 5.2.2 LTS / 3.13.13 | `dbbf836ad4b1025f14a2b3b504c43903f39e0b04` | 1.0.0 / 1.0.2 | Failed 3/3 |

External Python 3.13.12; uv 0.11.19; MCP SDK 1.30.0; docutils 0.23; HTTPX 0.28.1. Complete dependency versions are in the evidence files.

### Reproduction

1. Build/install the official Extension from `addon/blender_mcp_addon` at either commit, start its bridge, and configure a stdio client to launch the same commit's external `blender-mcp`. Point `BLENDER_MCP_HOST` and `BLENDER_MCP_PORT` at the bridge.
2. Confirm `get_objects_summary` returns the scene objects.
3. Call `get_python_api_docs`:

```json
{"identifier":"bpy.types.Object.location"}
```

4. Run these controls with the same tool:

```json
{"identifier":"bpy.ops.mesh.primitive_cube_add"}
```

```json
{"identifier":"bpy.types.Object.Object.location"}
```

The automated reproducer is `scripts/test_upstream_split.py --blender <blender.exe> --upstream-ref <full commit above> --label <unique-label>` in the evidence repository.

### Expected

`bpy.types.Object.location` returns `found: true` and location documentation without repeating `Object`.

### Actual

All six standard member queries return:

```json
{
  "kind":"partial",
  "found":false,
  "identifier":"bpy.types.Object.location",
  "parent":"bpy.types.Object",
  "available":["Object"],
  "submodules":[]
}
```

Both controls succeed in every session (6/6 each). The duplicated class identifier returns `kind: definition`, `found: true` for the location attribute. This is a workaround and confirms that the documentation is present.

### Evidence and source location

- [5.1 official split results](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/main/docs/upstream-issues/evidence/blender-5.1-official.json), [5.2 official split results](https://github.com/psiQAQ/blender_mcp-setup-guide/blob/main/docs/upstream-issues/evidence/blender-5.2-official.json): actual response fields, connection/control results, exact source hashes and versions. Attach these token-free, path-free files when posting.
- [Pinned get_python_api_docs.py](https://projects.blender.org/lab/blender_mcp/src/commit/dbbf836ad4b1025f14a2b3b504c43903f39e0b04/mcp/blmcp/tools/get_python_api_docs.py): intra-file lookup selects `bpy.types.Object.rst` and searches its doctree for the remaining `location` identifier.
- [Pinned rst_parse_docs.py](https://projects.blender.org/lab/blender_mcp/src/commit/dbbf836ad4b1025f14a2b3b504c43903f39e0b04/mcp/blmcp/tools_helpers/rst_parse_docs.py), `_find_definition`: lookup encounters the root `Object` class container, whose name does not match `location` at that level. Bundled `data/api/bpy.types.Object.rst` contains `.. class:: Object(ID)` with a nested `.. attribute:: location`.
- Proposed direction: account for the root class container when resolving members while preserving operator and explicitly nested-definition lookups. No upstream code was patched.

## Submission note

This local draft has not been posted. The official README directs reports to the [Blender MCP issue tracker](https://projects.blender.org/lab/blender_mcp/issues). Both fixed Git trees were checked for `.github`, `.gitea` and `.forgejo` issue templates; none were present. The upstream issue creation webpage was inaccessible to the reading tool on 2026-10-10, so server-provided templates could not be checked. Apply any form requirements shown after signing in.
