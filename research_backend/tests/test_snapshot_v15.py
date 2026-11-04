import pytest
from datetime import datetime, timezone, timedelta
from snapshot_v15 import extract, OFFICIAL_URL

def test_cache_freshness_and_provenance():
    v={'sourceUrl':OFFICIAL_URL,'updatedAt':datetime.now(timezone.utc).isoformat(),
       'stale':False,'draws':[{'issue':'26001','date':'2026-01-01','number':'00123'}]}
    assert extract(v)[0]['number']=='00123'
    with pytest.raises(ValueError):extract({**v,'sourceUrl':'https://evil.test'})
    with pytest.raises(ValueError):extract({**v,'stale':True})
    with pytest.raises(ValueError):extract({**v,'updatedAt':(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()})
