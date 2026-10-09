# Issue title

GUI render_thumbnail_to_path can render at the original resolution instead of the thumbnail resolution

## Issue body

### Environment

Tested on Windows x64 on 2026-10-10 with the **unmodified official `mcp` Extension and an external uv-installed `blender-mcp` stdio server**. Each row used three fresh GUI processes with isolated profiles and random localhost bridge ports. No integrated Extension or `_vendor` was installed. Installed official source hashes match the archived Git source.

| Blender / bundled Python | Upstream commit | Extension / server | Incorrect thumbnails |
| --- | --- | --- | --- |
| 5.1.1 / 3.13.9 | v1.0.3, `2cea8d566dde07fbac28a61d698909d69724e853` | 1.0.3 / 1.0.3 | 8/9; sessions 3/3, 2/3, 3/3 |
| 5.2.2 LTS / 3.13.13 | `dbbf836ad4b1025f14a2b3b504c43903f39e0b04` | 1.0.0 / 1.0.2 | 7/9; sessions 3/3, 3/3, 1/3 |

External Python 3.13.12; uv 0.11.19; MCP SDK 1.30.0; HTTPX 0.28.1; docutils 0.23. Cycles CPU, two original samples, default camera/cube and a 400 × 300 scene. Full dependency and graphics versions are in the evidence files.

### Reproduction

1. Build the official Extension from `addon/blender_mcp_addon` at either commit using `blender --command extension build`, install its ZIP through Blender's Extensions interface and start its bridge.
2. Install the same commit's `mcp` project in a separate uv tool environment. Configure a stdio client to launch that environment's `blender-mcp`, with `BLENDER_MCP_HOST` and `BLENDER_MCP_PORT` matching the bridge.
3. Confirm `get_objects_summary` returns the Cube. Call `execute_blender_code`:

```json
{"code":"import bpy\ns=bpy.context.scene\ns.render.engine='CYCLES'\ns.cycles.device='CPU'\ns.cycles.samples=2\ns.render.resolution_x=400\ns.render.resolution_y=300\ns.render.resolution_percentage=100\ns.render.image_settings.file_format='PNG'\nresult={'has_camera':s.camera is not None}"}
```

4. With `has_camera: true`, call `render_thumbnail_to_path` three times using distinct filenames:

```json
{"output_path":"thumbnail-repro.png"}
```

Inspect the PNG at the returned `filepath`. Repeat in fresh GUI sessions because this is timing-dependent. The automated reproducer in the evidence repository is:

```text
python scripts/test_upstream_split.py --blender <blender.exe> --upstream-ref <full commit above> --label <unique-label>
```

### Expected

The longest dimension is at most 320, here 320 × 240. Original scene settings are restored after completion.

### Actual

The tool completes successfully and returns a filepath, but 15/18 PNGs are **400 × 300**. Three PNGs are correctly 320 × 240. All have visible pixel variation, and original render settings are restored after every call.

Representative response, with its temporary directory redacted:

```json
{"filepath":"<MCP temporary directory>/thumbnail-1.png"}
```

### Evidence and source location

- [5.1 official split results](evidence/blender-5.1-official.json), [5.2 official split results](evidence/blender-5.2-official.json): per-call verdicts, PNG dimensions/SHA-256, pixel range, restoration checks, dependencies and source hashes. Attach these path-free, token-free files when posting.
- `mcp/blmcp/tools/render_thumbnail_to_path_toolcode.py`, `main()`, around lines 89–112: thumbnail settings are applied inside `_backup_attrs_and_assign_multi`, but GUI rendering uses `INVOKE_DEFAULT`. The context exits before the asynchronous job completes. Its deferred handler keeps/restores `filepath`, while the other settings have already been restored.
- Keeping all temporary settings until completion/cancellation is a proposed fix direction, not a tested upstream patch. Background rendering was not part of this reproduction.

## Submission note

This local draft has not been posted. Both fixed Git trees were checked for `.github`, `.gitea` and `.forgejo` issue templates; none were present. The upstream issue creation webpage was inaccessible to the reading tool on 2026-10-10, so server-provided templates could not be checked. Apply any form requirements shown after signing in.
