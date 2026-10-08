# Dependency Policy

Use this policy when a Blender Extension or its independent service needs third-party Python packages.

## Core rules

- Do not install packages into Blender bundled Python global `site-packages`.
- Bundle dependencies imported in Blender as manifest wheels matched to the Python ABI and platform.
- Store writable data with `bpy.utils.extension_path_user(...)`.
- Do not silently install dependencies in `register()`, module import, or add-on enable flow.
- Required dependencies are imported directly; optional dependencies are checked when the corresponding capability is invoked.
- Delay optional imports until an operator `execute()` method or a concrete business function needs them.

## Template defaults

- The default template has no third-party dependencies or installation UI.
- When required, list bundled wheels in `blender_manifest.toml` and preserve their licenses.
- Missing optional packages produce a clear capability-specific message.

## Independent MCP process

The integration starts Blender's bundled Python with `-I -S -B`. Its launcher explicitly initializes the private runtime with `site.addsitedir`, including `.pth` and native-library setup. The Blender process imports the standard-library integration code and official bridge.

Build inputs pin dependency versions, wheel checksums, and the official upstream commit. Preserve package data and `.dist-info`; verify native imports and a real MCP session on the target platform.

## Release guidance

- Do not ship a release build with `deps/site-packages` copied into the source tree by default.
- Prefer `wheels = [...]` in `blender_manifest.toml` for published extensions.
- Declare permissions for the actual capability and check `bpy.app.online_access` before internet access.
- For `torch`, `opencv-python`, `scipy`, `open3d`, CUDA packages, and other heavy binary dependencies, prefer an external Python service or environment.
- Communicate with heavy external environments through `subprocess`, sockets, HTTP, or MCP instead of forcing them into Blender Python.
