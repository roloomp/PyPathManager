import json
import subprocess


def run(cmd, timeout):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(str(e))
    if r.returncode != 0:
        err = r.stderr.strip().splitlines()
        raise RuntimeError(err[-1] if err else "команда завершилась с ошибкой")
    return r.stdout


def _pip(exe, args, timeout):
    return run([exe, "-m", "pip", *args, "--disable-pip-version-check"], timeout)


def get_libs(exe):
    out = _pip(exe, ["list", "--format=json"], 60)
    return sorted(json.loads(out), key=lambda x: x["name"].lower())


def update_libs(exe, names):
    _pip(exe, ["install", "--upgrade", *names], 600)


def delete_libs(exe, names):
    _pip(exe, ["uninstall", "-y", *names], 300)


def install_libs(exe, names):
    _pip(exe, ["install", *names], 600)


def get_outdated(exe):
    out = _pip(exe, ["list", "--outdated", "--format=json"], 120)
    return {x["name"].lower(): x["latest_version"] for x in json.loads(out)}


def install_from_file(exe, path):
    _pip(exe, ["install", "-r", path], 600)


def freeze(exe):
    return _pip(exe, ["freeze"], 60)
