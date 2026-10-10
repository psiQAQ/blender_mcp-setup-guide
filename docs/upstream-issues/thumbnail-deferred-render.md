# Issue title

GUI render_thumbnail_to_path can render at the original resolution instead of the thumbnail resolution

# Issue body

````markdown
# Environment

Tested on Windows x64 on 2026-10-10 with the **unmodified official `mcp` Extension and an external uv-installed `blender-mcp` stdio server**, both built from the upstream commits below. Each version used three fresh GUI processes with isolated profiles and random localhost bridge ports. Installed official source hashes match the corresponding Git source.

| Blender / bundled Python | Upstream commit | Extension / server | Incorrect thumbnails |
| --- | --- | --- | --- |
| 5.1.1 / 3.13.9 | v1.0.3, `2cea8d566dde07fbac28a61d698909d69724e853` | 1.0.3 / 1.0.3 | 8/9; sessions 3/3, 2/3, 3/3 |
| 5.2.2 LTS / 3.13.13 | `dbbf836ad4b1025f14a2b3b504c43903f39e0b04` | 1.0.0 / 1.0.2 | 7/9; sessions 3/3, 3/3, 1/3 |

External Python 3.13.12; uv 0.11.19; MCP SDK 1.30.0; HTTPX 0.28.1; docutils 0.23. GPU: NVIDIA GeForce RTX 4070 Ti SUPER; graphics version: OpenGL 4.6.0 NVIDIA 572.83. Rendering used Cycles CPU with two original samples, the default camera/cube and a 400 × 300 scene.

# Reproduction

1. Build the official Extension from `addon/blender_mcp_addon` at either commit using `blender --command extension build`, install its ZIP through Blender's Extensions interface and start its bridge.
2. Install the same commit's `mcp` project in a separate uv tool environment. Configure a stdio client to launch that environment's `blender-mcp`, with `BLENDER_MCP_HOST` and `BLENDER_MCP_PORT` matching the bridge.
3. Confirm `get_objects_summary` returns the Cube. Call `execute_blender_code`:

```json
{"code":"import bpy\ns=bpy.context.scene\ns.render.engine='CYCLES'\ns.cycles.device='CPU'\ns.cycles.samples=2\ns.render.resolution_x=400\ns.render.resolution_y=300\ns.render.resolution_percentage=100\ns.render.image_settings.file_format='PNG'\nresult={'has_camera':s.camera is not None}"}
```

4. With `has_camera: true`, call `render_thumbnail_to_path` three times using `thumbnail-1.png`, `thumbnail-2.png` and `thumbnail-3.png` as distinct filenames. For example:

```json
{"output_path":"thumbnail-1.png"}
```

After each call completes, inspect the PNG at the returned `filepath` and check the scene's render settings. Repeat in fresh GUI sessions because the incorrect dimensions are intermittent.

# Expected

The longest dimension is at most 320, here 320 × 240. Original scene settings are restored after completion.

# Actual

The tool completes successfully and returns a filepath, but **15/18 PNGs have incorrect dimensions**: 12 are 400 × 300 and three are 400 × 240. Three PNGs are correctly 320 × 240. All have visible pixel variation, and original render settings are restored after every call.

# Evidence

The following dimensions were read from the actual PNG files after each tool call. Each session was a fresh GUI process; the three calls within it used the same scene.

| Blender | GUI session | First PNG | Second PNG | Third PNG | Incorrect dimensions |
| --- | --- | --- | --- | --- | --- |
| 5.1.1 | 1 | 400 × 300 | 400 × 300 | 400 × 300 | 3/3 |
| 5.1.1 | 2 | 400 × 300 | 320 × 240 | 400 × 300 | 2/3 |
| 5.1.1 | 3 | 400 × 300 | 400 × 300 | 400 × 240 | 3/3 |
| 5.2.2 LTS | 1 | 400 × 300 | 400 × 240 | 400 × 300 | 3/3 |
| 5.2.2 LTS | 2 | 400 × 300 | 400 × 240 | 400 × 300 | 3/3 |
| 5.2.2 LTS | 3 | 400 × 300 | 320 × 240 | 320 × 240 | 1/3 |

Scene reading succeeded in all six sessions. Original render settings were restored after all 18 calls, including the 15 calls that produced incorrect dimensions.

Representative response, with its temporary directory redacted:

```json
{"status":"ok","filepath":"<MCP temporary directory>/thumbnail-1.png"}
```

# Relevant upstream code

[Pinned thumbnail implementation](https://projects.blender.org/lab/blender_mcp/src/commit/dbbf836ad4b1025f14a2b3b504c43903f39e0b04/mcp/blmcp/tools/render_thumbnail_to_path_toolcode.py), `main()`, around lines 89–112: thumbnail settings are applied inside `_backup_attrs_and_assign_multi`, while GUI rendering uses `INVOKE_DEFAULT`. Its deferred handler keeps/restores `filepath`.

Possible cause: the settings context exits before the asynchronous render finishes, allowing the original dimensions to be restored while rendering is still starting. Keeping all temporary settings until completion/cancellation is a proposed fix direction; no upstream patch was applied or tested. Background rendering was not part of this reproduction.
````

# Submission note (not part of the issue body)

This local draft has not been posted. The official README directs reports to the [Blender MCP issue tracker](https://projects.blender.org/lab/blender_mcp/issues). Both fixed Git trees were checked for `.github`, `.gitea` and `.forgejo` issue templates; none were present. The upstream issue creation webpage was inaccessible to the reading tool on 2026-10-10, so server-provided templates could not be checked. Apply any form requirements shown after signing in.
