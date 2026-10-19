import json
import subprocess


def _pip(exe, args, timeout):
    try:
        r = subprocess.run([exe, "-m", "pip", *args, "--disable-pip-version-check"],
                           capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(str(e))
    if r.returncode != 0:
        err = r.stderr.strip().splitlines()
        raise RuntimeError(err[-1] if err else "pip завершился с ошибкой")
    return r.stdout


def get_libs(exe):
    out = _pip(exe, ["list", "--format=json"], 60)
    return sorted(json.loads(out), key=lambda x: x["name"].lower())


def update_libs(exe, names):
    _pip(exe, ["install", "--upgrade", *names], 600)


def delete_libs(exe, names):
    _pip(exe, ["uninstall", "-y", *names], 300)


def get_outdated(exe):
    out = _pip(exe, ["list", "--outdated", "--format=json"], 120)
    return {x["name"].lower(): x["latest_version"] for x in json.loads(out)}


def install_from_file(exe, path):
    _pip(exe, ["install", "-r", path], 600)
