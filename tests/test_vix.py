from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from modules.vix import fetch_vix, parse_vix_csv, vix_zone
from modules.gauge_components import build_vix_gauge

TODAY = date(2026, 11, 6)
FRED = 'observation_date,VIXCLS\n2026-11-04,16.61\n2026-11-05,.\n'
CBOE = 'DATE,OPEN,HIGH,LOW,CLOSE\n11/05/2026,20,21,18,19.25\n'


def response(body):
    result = MagicMock()
    result.__enter__.return_value.read.return_value = body
    return result


@pytest.mark.parametrize('value,label', [(10,'Lav'),(15,'Moderat'),(20,'Forhøjet'),
    (30,'Høj'),(40,'Meget høj'),(120.25,'Meget høj')])
def test_raw_value_and_zones(value, label):
    snap = parse_vix_csv(f'observation_date,VIXCLS\n2026-11-05,{value}\n', 'FRED', today=TODAY)
    assert snap.value == value
    assert snap.label == label
    figure = build_vix_gauge(value, label)
    assert figure.data[0].value == value
    assert figure.data[0].gauge.threshold.value == value
    assert figure.data[0].number.suffix == ''
    assert figure.data[0].gauge.axis.range[1] >= value
    assert figure.layout.annotations[-1].font.color == vix_zone(value)[1]


@pytest.mark.parametrize('source,body,expected', [('FRED', FRED,16.61),
    ('FRED', FRED.replace('observation_date','DATE'),16.61),('Cboe',CBOE,19.25)])
def test_source_formats(source, body, expected):
    snap = parse_vix_csv(body, source, today=TODAY)
    assert snap.value == expected
    assert snap.source == source
    assert snap.source_url.startswith('https://')


@pytest.mark.parametrize('body', ['<html>no</html>', 'date,other\n2026-11-05,20',
    'observation_date,VIXCLS\n2026-11-06,.',
    *[f'observation_date,VIXCLS\n2026-11-05,{v}' for v in ['nan','inf','-1','0','bad']],
    'observation_date,VIXCLS\n2026-11-07,20',
    'observation_date,VIXCLS\n2026-10-01,20',
    'observation_date,VIXCLS\ninvalid,20'])
def test_reject_bad_or_stale_data(body):
    with pytest.raises(ValueError):
        parse_vix_csv(body, 'FRED', today=TODAY)


def test_unsorted_rows_and_holiday():
    snap = parse_vix_csv('observation_date,VIXCLS\n2026-11-03,18\n2026-11-02,20\n', 'FRED', today=TODAY)
    assert snap.observed_on == date(2026,11,3)
    assert snap.value == 18


def test_primary_success_makes_one_request():
    with patch('modules.vix.urlopen', return_value=response(FRED.encode())) as request:
        snap = fetch_vix(today=TODAY)
    assert snap.source == 'FRED'
    assert request.call_count == 1
    assert request.call_args.kwargs['timeout'] == 5


@pytest.mark.parametrize('first', [URLError('blocked'), TimeoutError(),
    response(b'<html>blocked</html>'),
    response(b'observation_date,VIXCLS\n2026-10-01,20')])
def test_fallback_to_cboe(first):
    with patch('modules.vix.urlopen', side_effect=[first, response(CBOE.encode())]) as request:
        snap = fetch_vix(today=TODAY)
    assert request.call_count == 2
    assert snap.source == 'Cboe'
    assert snap.value == 19.25


def test_both_fail_gives_gray_na_without_pointer():
    with patch('modules.vix.urlopen', side_effect=URLError('offline')) as request:
        snap = fetch_vix(today=TODAY)
    assert request.call_count == 2
    assert snap.value is None and snap.error
    figure = build_vix_gauge(snap.value, snap.label)
    assert figure.data[0].mode == 'gauge'
    assert figure.data[0].gauge.threshold.value is None
    assert len(figure.data[0].gauge.steps) == 1
    assert any(a.text == '<b>N/A</b>' for a in figure.layout.annotations)


def test_oversize_response_falls_back():
    with patch('modules.vix.urlopen', side_effect=[response(b'x'*2_000_001), response(CBOE.encode())]):
        assert fetch_vix(today=TODAY).source == 'Cboe'
