import json
from pathlib import Path
claims=json.loads(Path(__file__).with_name('claims.json').read_text(encoding='utf-8'))
stale=sum(x['expected']=='OUTDATED' for x in claims)
results=('| Metric | Result |\n|---|---:|\n| Labeled claims | %d |\n| Expected stale examples | %d |\n| Precision | n/a (run the live verifier with credentials) |\n| Recall | n/a (run the live verifier with credentials) |\n| Average cost / answer | n/a (Bifrost usage ingestion not enabled) |\n| Average latency | n/a (live execution required) |' % (len(claims), stale))
print(results)
Path(__file__).with_name('results.md').write_text('# FreshCheck eval\n\n'+results+'\n', encoding='utf-8')
