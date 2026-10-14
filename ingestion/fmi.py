"""Bounded FMI feasibility requests and strict timevaluepair response inspection."""

import hashlib
import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

ENDPOINT = "https://opendata.fmi.fi/wfs"
QUERY = "fmi::observations::weather::timevaluepair"
NS = {"wfs": "http://www.opengis.net/wfs/2.0", "om": "http://www.opengis.net/om/2.0",
      "gml": "http://www.opengis.net/gml/3.2", "target": "http://xml.fmi.fi/namespace/om/atmosphericfeatures/1.1",
      "wml": "http://www.opengis.net/waterml/2.0", "ows": "http://www.opengis.net/ows/1.1"}
XLINK = "{http://www.w3.org/1999/xlink}href"
MAX_BYTES = 2_000_000


def utc_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("Use an explicit UTC timestamp, e.g. 2025-01-01T00:00:00Z")
    return parsed.astimezone(timezone.utc)


def request_parameters(start: str, end: str, station: str | None = None,
                       place: str | None = None, timestep: int = 60) -> dict:
    first, last = utc_time(start), utc_time(end)
    if not timedelta(0) < last - first <= timedelta(days=7):
        raise ValueError("Feasibility queries require a positive interval of at most seven days")
    if timestep not in (10, 60) or any(t.minute or t.second or t.microsecond for t in (first, last)):
        raise ValueError("Use whole UTC-hour boundaries and a 10- or 60-minute timestep")
    if bool(station) == bool(place):
        raise ValueError("Select exactly one station ID or discovery place")
    if station is not None and not station.isdecimal():
        raise ValueError("FMI station ID must contain digits only")
    return {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "storedquery_id": QUERY, "parameters": "t2m", "starttime": start, "endtime": end,
            "timestep": str(timestep), **({"fmisid": station} if station else {"place": place})}


def download(parameters: dict, attempts: int = 3, timeout: int = 20) -> tuple[bytes, dict]:
    if not 1 <= attempts <= 3 or not 1 <= timeout <= 30:
        raise ValueError("Invalid bounded request settings")
    url = ENDPOINT + "?" + urllib.parse.urlencode(parameters)
    request = urllib.request.Request(url, headers={"User-Agent": "FinnishEnergyThesis/0.1 (source feasibility)",
                                                  "Accept": "application/xml,text/xml"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ValueError("FMI response exceeds the feasibility size limit")
                return payload, {"request_url": url, "http_status": response.status,
                                 "content_type": response.headers.get("Content-Type"), "attempts": attempt,
                                 "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt == attempts:
                raise ValueError(f"FMI HTTP {exc.code} after {attempt} attempt(s)") from None
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            if attempt == attempts:
                raise ValueError(f"FMI connection failed after {attempt} attempt(s)") from None
        time.sleep(min(2 ** (attempt - 1), 4))
    raise AssertionError("unreachable")


def inspect_response(payload: bytes, start: str, end: str, station: str | None = None,
                     timestep: int = 60) -> dict:
    """Inspect points in [start,end); FMI can return the inclusive end point."""
    if timestep not in (10, 60):
        raise ValueError("Unsupported timestep")
    first, last = utc_time(start), utc_time(end)
    if not timedelta(0) < last - first <= timedelta(days=7):
        raise ValueError("Invalid feasibility interval")
    if len(payload) > MAX_BYTES or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("Unsupported or oversized XML response")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        raise ValueError("FMI returned malformed XML") from None
    if root.tag != "{" + NS["wfs"] + "}FeatureCollection":
        raise ValueError("FMI did not return a WFS FeatureCollection")
    members = root.findall("wfs:member", NS)
    if not members:
        raise ValueError("FMI returned no observation members")
    stations = {}
    all_points = []
    seen_keys = set()
    duplicates = out_of_scope = missing_values = 0
    for member in members:
        locations = member.findall(".//target:Location", NS)
        if len(locations) != 1:
            raise ValueError("Missing or ambiguous FMI location metadata")
        location = locations[0]
        identities = [e.text for e in location.findall("gml:identifier", NS)
                      if e.get("codeSpace", "").endswith("/fmisid")]
        if len(identities) != 1 or not identities[0]:
            raise ValueError("Missing or ambiguous FMI station identity")
        station_id = identities[0]
        if station is not None and station_id != station:
            raise ValueError("FMI returned an unexpected station")
        name = next((e.text for e in location.findall("gml:name", NS)
                     if e.get("codeSpace", "").endswith("/name")), None)
        position = member.find(".//gml:Point/gml:pos", NS)
        prop = member.find(".//om:observedProperty", NS)
        link = prop.get(XLINK) if prop is not None else None
        if urllib.parse.parse_qs(urllib.parse.urlparse(link or "").query).get("param") != ["t2m"]:
            raise ValueError("FMI returned an unexpected or unidentifiable parameter")
        stations[station_id] = {"name": name, "coordinates_as_returned": position.text.strip() if position is not None else None,
                                "property_metadata_url": link}
        tvps = member.findall(".//wml:MeasurementTVP", NS)
        if not tvps:
            raise ValueError("FMI returned no temperature points")
        for point in tvps:
            raw_time = point.findtext("wml:time", namespaces=NS)
            raw_value = point.findtext("wml:value", namespaces=NS)
            if raw_time is None or raw_value is None:
                raise ValueError("Incomplete FMI point schema")
            timestamp = utc_time(raw_time)
            if not first <= timestamp < last:
                out_of_scope += 1
                continue
            key = (station_id, timestamp)
            if key in seen_keys:
                duplicates += 1
            seen_keys.add(key)
            try:
                numeric = float(raw_value)
            except ValueError:
                raise ValueError("Unexpected FMI measurement text") from None
            if not math.isfinite(numeric):
                if raw_value.lower() != "nan":
                    raise ValueError("Unsupported nonfinite FMI value")
                missing_values += 1
            all_points.append((station_id, timestamp, raw_value, math.isfinite(numeric)))
    expected = set()
    cursor = first
    while cursor < last:
        expected.add(cursor)
        cursor += timedelta(minutes=timestep)
    if any(timestamp not in expected for _, timestamp, _, _ in all_points):
        raise ValueError("FMI points do not match the requested time grid")
    summaries = {}
    for station_id in stations:
        observed = {t for s, t, _, _ in all_points if s == station_id}
        accepted = {t for s, t, _, valid in all_points if s == station_id and valid}
        summaries[station_id] = {"expected_samples": len(expected), "returned_distinct_samples": len(observed),
                                 "valid_samples": len(accepted), "absent_samples": len(expected - observed),
                                 "missing_value_samples": len(observed - accepted)}
    canonical = [[s, t.isoformat(), v] for s, t, v, _ in sorted(all_points)]
    return {"station_metadata": stations, "coverage_by_station": summaries,
            "point_rows_in_scope": len(all_points), "duplicate_key_rows": duplicates,
            "out_of_scope_points": out_of_scope, "nonfinite_samples": missing_values,
            "keyed_observation_sha256": hashlib.sha256(json.dumps(canonical, separators=(",", ":")).encode()).hexdigest(),
            "response_timestamp": root.get("timeStamp"), "time_basis": "explicit UTC point observations",
            "temperature_representation": "sampled observations; timestep is not an averaging operation"}


def acquire_sample(parameters: dict, raw_dir: Path, manifest_dir: Path) -> tuple[dict, Path]:
    payload, retrieval = download(parameters)
    digest = hashlib.sha256(payload).hexdigest()
    raw_dir.mkdir(parents=True, exist_ok=True)
    snapshot = raw_dir / (digest + ".xml")
    try:
        with snapshot.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if snapshot.read_bytes() != payload:
            raise ValueError("Existing content snapshot does not match its hash")
    manifest = {"audit_version": "0.1.0", "source": "FMI", "parameters": parameters,
                "response_sha256": digest, "response_bytes": len(payload), "snapshot_file": snapshot.name,
                "retrieval": retrieval, "licence_url": "https://en.ilmatieteenlaitos.fi/open-data-licence",
                "attribution": "Finnish Meteorological Institute, CC BY 4.0; inspected source observations",
                "status": "acquired_not_validated"}
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / (uuid4().hex + ".json")
    # Preserve acquisition evidence even when schema validation fails.
    try:
        manifest["inspection"] = inspect_response(payload, parameters["starttime"], parameters["endtime"],
                                                   parameters.get("fmisid"), int(parameters["timestep"]))
        manifest["status"] = "inspected"
    except ValueError as exc:
        manifest["status"] = "inspection_failed"
        manifest["error"] = str(exc)
        raise
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest, manifest_path
