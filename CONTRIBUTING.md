# Contributing

Use a branch for changes and keep the supplied license/provenance notices. Run `python -m unittest discover -s tests -v` and `python tools/build_addon.py` before opening a pull request. A failing original-hash check means a supplied file changed; investigate and intentionally update the hash record when releasing a reviewed revision rather than silently bypassing it.

For Blender/Unreal issues provide the full traceback, application version, reproduction settings, input dimensions and a minimal scene where possible. Remove personal paths, credentials and proprietary assets before uploading a reproduction. Separate visual asset defects from application API incompatibilities.

Do not commit generated `.blend`, FBX or ZIP exports, engine caches, secrets or unlicensed third-party assets. Do not describe an engine target as verified until it has actually been tested.
