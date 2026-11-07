"""Region defaults and named cross-section presets (spec §2.1).

Numbers are scenery defaults grounded in common standards (EU/RASt, TR/KGM, UK, US/AASHTO,
NACTO); they are not a substitute for engineering design. Imperial values are exact.
"""
from __future__ import annotations
from .section import Band, BandKind, CrossSection, LineSpec

FT, INCH = 0.3048, 0.0254

REGIONS: dict[str, dict] = {
    'EU': dict(drive='RHT', lane=3.25, lane_rural=3.50, crossfall=0.025, gutter=0.50, reveal=0.12, curb_top=0.15,
               sidewalk=3.00, marking=0.12, centre='DASH_3_6', lane_line='DASH_3_6', edge='SOLID', colour='WHITE'),
    'TR': dict(drive='RHT', lane=3.25, lane_rural=3.50, crossfall=0.025, gutter=0.50, reveal=0.15, curb_top=0.15,
               sidewalk=3.50, marking=0.12, centre='DASH_3_6', lane_line='DASH_3_6', edge='SOLID', colour='WHITE'),
    'UK': dict(drive='LHT', lane=3.25, lane_rural=3.65, crossfall=0.025, gutter=0.30, reveal=0.125, curb_top=0.125,
               sidewalk=3.00, marking=0.10, centre='DASH_4_8', lane_line='DASH_4_8', edge='SOLID', colour='WHITE'),
    'US': dict(drive='RHT', lane=11 * FT, lane_rural=12 * FT, crossfall=0.020, gutter=2 * FT, reveal=6 * INCH,
               curb_top=6 * INCH, sidewalk=12 * FT, marking=6 * INCH, centre='SOLID', lane_line='DASH_3_9', edge='SOLID',
               colour='YELLOW'),
}


def region(name: str) -> dict:
    if name not in REGIONS:
        raise ValueError(f'Unknown region {name!r}; use one of {sorted(REGIONS)}.')
    return REGIONS[name]


def _curb(r: dict, kind: str = 'BARRIER') -> Band:
    return Band(BandKind.CURB, 0.0, (('reveal', r['reveal']), ('setback', 0.03), ('top', r['curb_top']), ('type', kind)))


def urban_street(region_name: str = 'EU', lanes_per_side: int = 1, median: float = 0.0,
                 sidewalk: float | None = None) -> CrossSection:
    """Urban street: lanes, gutter, barrier curb and sidewalk on both sides."""
    r = region(region_name)
    if not 1 <= lanes_per_side <= 3:
        raise ValueError('Urban streets support 1–3 lanes per side.')
    w = r['marking']
    lane_line = LineSpec('LANE', 0.0, w, r['lane_line'])
    half = []
    for k in range(lanes_per_side):
        half.append(Band(BandKind.LANE, r['lane'], (), (lane_line,) if k > 0 else ()))
    half += [Band(BandKind.GUTTER, r['gutter']), _curb(r),
             Band(BandKind.SIDEWALK, r['sidewalk'] if sidewalk is None else sidewalk)]
    centre = () if median > 0 else (
        (LineSpec('CENTRE', -0.1, w, 'SOLID', r['colour']), LineSpec('CENTRE', 0.1, w, 'SOLID', r['colour']))
        if r['centre'] == 'SOLID' else (LineSpec('CENTRE', 0.0, w, r['centre'], r['colour']),))
    med = (Band(BandKind.MEDIAN_FLUSH, median),) if median > 0 else ()
    name = f'Street_{2 * lanes_per_side}L' + (f'_M{round(median * 100)}' if median else '')
    return CrossSection(name, region_name, tuple(half), tuple(half), med, r['crossfall'], drive_side=r['drive'],
                        centre_lines=centre)


def rural_road(region_name: str = 'EU', embankment: float = 1.0) -> CrossSection:
    """Two-lane rural road (RQ11-like): lanes, edge lines, bankett and embankment or ditch."""
    r = region(region_name)
    w = r['marking']
    lane = Band(BandKind.LANE, r['lane_rural'], (), (LineSpec('EDGE', r['lane_rural'] - 0.25 - w / 2, w, 'SOLID'),))
    side = [lane, Band(BandKind.BANKETT, 1.5, (('slope', 0.06),))]
    if embankment > 0:
        side.append(Band(BandKind.EMBANKMENT, 0.0, (('height', embankment), ('ratio', 1.5))))
    else:
        side.append(Band(BandKind.DITCH, 0.0, (('bottom', 0.5), ('depth', 0.6), ('ratio', 2.0))))
    centre = (LineSpec('CENTRE', 0.0, w, r['centre'] if r['centre'] != 'SOLID' else 'DASH_3_9', r['colour']),)
    return CrossSection('Rural_2L', region_name, tuple(side), tuple(side), (), r['crossfall'],
                        drive_side=r['drive'], centre_lines=centre)


def highway(region_name: str = 'EU', lanes_per_side: int = 2, median: float = 4.0) -> CrossSection:
    """Dual carriageway: flush median (barrier added as a separate solid), lanes, hard shoulder, bankett, embankment."""
    r = region(region_name)
    w = max(r['marking'], 0.15)
    lane_w = 3.75 if region_name != 'US' else 12 * FT
    half = []
    for k in range(lanes_per_side):
        lines = (LineSpec('EDGE', 0.25 + w / 2, w, 'SOLID'),) if k == 0 else (LineSpec('LANE', 0.0, w, 'DASH_6_12'),)
        half.append(Band(BandKind.LANE, lane_w, (), lines))
    half += [Band(BandKind.SHOULDER_PAVED, 3.0, (('slope', 0.04),), (LineSpec('EDGE', 0.0, w * 2, 'SOLID'),)),
             Band(BandKind.BANKETT, 1.5, (('slope', 0.06),)),
             Band(BandKind.EMBANKMENT, 0.0, (('height', 2.0), ('ratio', 2.0)))]
    return CrossSection(f'Highway_{2 * lanes_per_side}L', region_name, tuple(half), tuple(half),
                        (Band(BandKind.MEDIAN_FLUSH, median),), r['crossfall'], drive_side=r['drive'],
                        centre_lines=())


PRESETS = {
    'URBAN_2L': lambda reg: urban_street(reg, 1),
    'URBAN_4L': lambda reg: urban_street(reg, 2),
    'URBAN_4L_MEDIAN': lambda reg: urban_street(reg, 2, median=2.0),
    'RURAL_2L': lambda reg: rural_road(reg, 1.0),
    'RURAL_2L_DITCH': lambda reg: rural_road(reg, 0.0),
    'HIGHWAY_4L': lambda reg: highway(reg, 2),
}


def preset(name: str, region_name: str = 'EU') -> CrossSection:
    if name not in PRESETS:
        raise ValueError(f'Unknown section preset {name!r}; use one of {sorted(PRESETS)}.')
    return PRESETS[name](region_name)
