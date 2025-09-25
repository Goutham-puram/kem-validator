import re
from pathlib import Path

import court_validator_base as cvb

def main():
    vf = cvb.ValidatorFactory('courts_config.json')
    validator = vf.get_validator('KEM')
    text = Path('sample-files/KEM_valid_only.txt').read_text(encoding='utf-8')
    results = validator.validate_text(text)

    prefix = 'KEM'
    def is_court_row(r):
        raw = r.get('raw','') or ''
        if not raw:
            return False
        if not (raw.startswith(f"{prefix}\t") or re.match(rf"^\s*{re.escape(prefix)}\s+", raw)):
            return False
        if int(r.get('digits_count', 0) or 0) <= 0:
            return False
        if not (r.get('kem_id_raw') or '').strip():
            return False
        return True

    court_rows = [r for r in results if is_court_row(r)]
    print('total:', len(results))
    print('kem_rows:', len(court_rows))
    print('failed:', sum(1 for r in court_rows if not r['is_valid']))
    for r in results[:6]:
        print(r['line_number'], r['kem_id_raw'], r['digits_count'], r['is_valid'], r['fail_reason'], '|', r['raw'][:40])

if __name__ == '__main__':
    main()

