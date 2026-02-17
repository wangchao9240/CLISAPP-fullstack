#!/usr/bin/env python3
"""
Download NASA GPM IMERG V07B Half-hourly Late Run granules for today (UTC) via authenticated HTTPS.
Requires ~/.netrc with: machine urs.earthdata.nasa.gov login <user> password <pass>
Saves a few latest granules to phase2-data-pipeline/data/raw/gpm_imerg/YYYYMMDD/
"""
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timedelta, timezone
import requests
from netrc import netrc

BASES = [
    'https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/IMERG/late/HH',
    'https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGHH_LATE.07'
]
OUT_ROOT = Path('data_pipeline/data/raw/gpm/imerg_hh')
DAILY_BASE = 'https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDE.07'
OUT_DAILY = Path('data_pipeline/data/raw/gpm/imerg_daily')

FILE_RE = re.compile(r"(3B-HHR-L\.MS\.MRG\.3IMERG\.(\d{8})-S\d{6}-E\d{6}\.V07B\.HDF5)")


def try_list(session: requests.Session, url: str, today_str: str) -> list[str]:
    r = session.get(url, timeout=60)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    names = []
    for m in re.finditer(FILE_RE, r.text):
        name = m.group(1)
        if name.startswith(f"3B-HHR-L.MS.MRG.3IMERG.{today_str}"):
            names.append(name)
    return sorted(set(names))


def list_today_files(session: requests.Session, today: datetime) -> tuple[str, list[str]]:
    yyyy = today.strftime('%Y')
    mm = today.strftime('%m')
    dd = today.strftime('%d')
    doy = today.strftime('%j')
    today_str = today.strftime('%Y%m%d')

    # Try IMERG/late/HH/YYYY/MM/DD
    for base in BASES:
        url = f"{base}/{yyyy}/{mm}/{dd}/"
        names = try_list(session, url, today_str)
        if names:
            return url.rstrip('/'), names
    # Try GPM_3IMERGHH_LATE.07/YYYY/DOY
    base = 'https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGHH_LATE.07'
    url = f"{base}/{yyyy}/{doy}/"
    names = try_list(session, url, today_str)
    if names:
        return url.rstrip('/'), names
    return '', []


def ensure_login(session: requests.Session) -> None:
    # Probe a small authenticated resource to trigger EDL login via redirect
    probe = f"{BASES[0]}/"
    resp = session.get(probe, allow_redirects=True, timeout=30)
    # If redirected to EDL oauth, prompt user to authorize
    if 'urs.earthdata.nasa.gov' in resp.url or resp.status_code in (401, 403):
        auth_url = (
            'https://urs.earthdata.nasa.gov/oauth/authorize?'
            'client_id=e2WVk8Pw6weeLUKZYOxvTQ&response_type=code&'
            'redirect_uri=https%3A%2F%2Fgpm1.gesdisc.eosdis.nasa.gov%2Fdata-redirect'
        )
        print('Authorization required for NASA GESDISC DATA ARCHIVE.')
        print('Open this link in a browser, log in, and click Authorize:')
        print(auth_url)
        raise SystemExit('After authorizing, re-run this script.')


def download_file(session: requests.Session, url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Exists: {dest}")
        return
    with session.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + '.part')
        with open(tmp, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
        print(f"Saved: {dest}")


def download_daily_yesterday(session: requests.Session) -> Path | None:
    OUT_DAILY.mkdir(parents=True, exist_ok=True)
    yday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    yyyy = yday.strftime('%Y')
    mm = yday.strftime('%m')
    dd = yday.strftime('%d')
    ymd = yday.strftime('%Y%m%d')
    url = f"{DAILY_BASE}/{yyyy}/{mm}/"
    r = session.get(url, timeout=60)
    r.raise_for_status()
    fname = f"3B-DAY-E.MS.MRG.3IMERG.{ymd}-S000000-E235959.V07B.nc4"
    if fname not in r.text:
        print('Daily file not yet listed, directory fetched but file missing:', fname)
        return None
    dest_dir = OUT_DAILY / yday.strftime('%Y%m%d')
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / fname
    download_file(session, f"{url}{fname}", dest)
    return dest


def main(max_granules: int = 4, mode: str = 'daily'):
    today = datetime.now(timezone.utc).date()
    session = requests.Session()
    session.trust_env = True
    session.verify = False 
    try:
        n = netrc()
        auth = n.authenticators('urs.earthdata.nasa.gov')
        if auth:
            session.auth = (auth[0], auth[2])
    except Exception:
        pass
    session.headers.update({'User-Agent': 'CLISApp-IMERG-Downloader/1.0'})

    ensure_login(session)

    if mode == 'daily':
        saved = download_daily_yesterday(session)
        if not saved:
            print('No daily file available yet.')
        return

    # fallback: half-hourly late run (original logic)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    base_day, files = list_today_files(session, datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc))
    if not files:
        print('No IMERG Late Run files listed for today yet (UTC). Try again later.')
        return

    # Download the last few granules (closest to now)
    to_get = files[-max_granules:]
    day_dir = OUT_ROOT / today.strftime('%Y%m%d')
    day_dir.mkdir(parents=True, exist_ok=True)

    for name in to_get:
        url = f"{base_day}/{name}"
        dest = day_dir / name
        download_file(session, url, dest)


if __name__ == '__main__':
    main()
