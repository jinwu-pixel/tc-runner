#!/usr/bin/env python3
"""
ims_sip_digest.py - QCAT 0x156E "IMS SIP Message" text dump -> compact verification digest.

WHY
  Heavy QCAT decode (~3 min / large .hdf) stays a token-0 batch step (qcat_fast_extract.ps1,
  foreground COM). This digester reduces each capture's 0x156E text (tens of KB) to only the
  override-verification-relevant lines with KST timestamps, so review reads a KB digest instead
  of re-scanning raw SIP/SDP per capture. Optional --expected diffs observed vs intended TC inputs.

INPUT  one or more QCAT-exported 0x156E text files (the '%MOBILE PARSED MESSAGE FILE' format from
       `qcat_fast_extract.ps1 -Codes 0x156E -Out <txt>`). Offline LS .qmdl (USER build) lack 0x156E,
       so there is nothing to digest from them - only online QXDM .hdf/.isf carry SIP.
       (see memory: reference_ims_sip_qcat_verification)
OUTPUT markdown digest to stdout; optional --json <file> for the machine 'observed' object.

USAGE
  python ims_sip_digest.py v2r_1302_sip.txt
  python ims_sip_digest.py *_sip.txt --expected expected.json
  python ims_sip_digest.py tc02_sip.txt --json tc02_observed.json

NOTE  QCAT timestamps are UTC; displayed as KST (UTC+9) by default (--utc to keep UTC).
      Pure stdlib. No QCAT/COM here.
"""
import re, json, argparse, datetime

HDR_RE = re.compile(
    r'^(?P<ts>\d{4}\s+\w{3}\s+\d+\s+[\d:.]+)\s+\[[0-9A-Fa-f]{2}\]\s+0x156E\s+'
    r'IMS SIP Message\s+--\s+(?P<typeres>\S+)')
KV_RE  = re.compile(r'^(?P<k>[A-Za-z][A-Za-z0-9 ]*?)\s*=\s*(?P<v>.*)$')
AUTH_RE = re.compile(r'(\b\w+)="([^"]*)"')

# QShrink (0x1FEB/0x1FFB) RILQ imsRadio path - used when 0x156E is absent
# (USER-build offline LS mask). Recovers IMS registration result, NOT on-wire SDP.
QSH_TS_RE = re.compile(
    r'^(?P<ts>\d{4}\s+\w{3}\s+\d+\s+[\d:.]+)\s+\[[0-9A-Fa-f]{2}\]\s+0x1F[EF]B\b')
REGCHG_RE = re.compile(
    r'onRegistrationChanged:\s*reg\s*=\s*RegistrationInfo\{'
    r'state:\s*(?P<state>[A-Z_]+),\s*errorCode:\s*(?P<ec>-?\d+)'
    r'(?:,\s*errorMessage:\s*(?P<emsg>[^,]*))?'
    r'(?:,\s*radioTech:\s*(?P<rat>[A-Za-z0-9_]+))?'
    r'(?:,\s*pAssociatedUris:\s*(?P<uris>[^}]*))?')
INT_MAX = '2147483647'   # imsRadio "unset / no error" sentinel


def parse_ts(s):
    s = re.sub(r'\s+', ' ', s.strip())
    try:
        return datetime.datetime.strptime(s, '%Y %b %d %H:%M:%S.%f')
    except ValueError:
        return None


def split_blocks(lines):
    """Yield (header_match, [block_lines]) per 0x156E packet."""
    cur_hdr, cur = None, []
    for ln in lines:
        m = HDR_RE.match(ln)
        if m:
            if cur_hdr is not None:
                yield cur_hdr, cur
            cur_hdr, cur = m, []
        elif cur_hdr is not None:
            cur.append(ln)
    if cur_hdr is not None:
        yield cur_hdr, cur


def hdr_val(sip_lines, name):
    pat = re.compile(r'^' + re.escape(name) + r':\s*(.*)$', re.I)
    for ln in sip_lines:
        m = pat.match(ln)
        if m:
            return m.group(1).strip()
    return None


def summarize_sdp(sip_lines):
    """Return dict of SDP media summary (offer/answer agnostic)."""
    rtpmap, fmtp, imageattr = {}, {}, {}
    media = []   # list of dict {kind, port, payloads}
    framerate = None
    for ln in sip_lines:
        if ln.startswith('m=audio') or ln.startswith('m=video'):
            toks = ln.split()
            kind = 'audio' if ln.startswith('m=audio') else 'video'
            port = toks[1] if len(toks) > 1 else '?'
            pts = toks[3:] if len(toks) > 3 else []
            media.append({'kind': kind, 'port': port, 'payloads': pts})
        elif ln.startswith('a=rtpmap:'):
            m = re.match(r'a=rtpmap:(\d+)\s+(\S+)', ln)
            if m:
                rtpmap[m.group(1)] = m.group(2)
        elif ln.startswith('a=fmtp:'):
            m = re.match(r'a=fmtp:(\d+)\s+(.*)', ln)
            if m:
                fmtp[m.group(1)] = m.group(2).strip()
        elif ln.startswith('a=imageattr:'):
            m = re.match(r'a=imageattr:(\d+).*?\[x=(\d+),y=(\d+)\]', ln)
            if m:
                imageattr[m.group(1)] = '%sx%s' % (m.group(2), m.group(3))
        elif ln.startswith('a=framerate:'):
            framerate = ln.split(':', 1)[1].strip()

    def codec_str(pts):
        seen, out = set(), []
        for pt in pts:
            if pt in seen:
                continue
            seen.add(pt)
            name = rtpmap.get(pt, 'pt' + pt)
            ms = ''
            fp = fmtp.get(pt, '')
            mm = re.search(r'mode-set=(\d+)', fp)
            if mm:
                ms = '(ms%s)' % mm.group(1)
            res = imageattr.get(pt)
            out.append(name + ms + (('@' + res) if res else ''))
        return '>'.join(out)

    audio = next((x for x in media if x['kind'] == 'audio'), None)
    video = next((x for x in media if x['kind'] == 'video'), None)
    return {
        'audio_port': audio['port'] if audio else None,
        'audio_codecs': codec_str(audio['payloads']) if audio else None,
        'video_port': video['port'] if video else None,
        'video_codecs': codec_str(video['payloads']) if video else None,
        'video_res': (imageattr.get(video['payloads'][0]) if video and video['payloads'] else None),
        'framerate': framerate,
    }


def parse_capture(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        lines = [l.rstrip('\n') for l in fh]
    ver = next((l.split(':', 1)[1].strip() for l in lines[:10]
                if l.startswith('%QCAT VERSION')), '?')
    recs = []
    for m, block in split_blocks(lines):
        ts = parse_ts(m.group('ts'))
        rec = {'ts': ts, 'typeres': m.group('typeres'),
               'meta': {}, 'sip_first': None, 'sip': []}
        in_sip = False
        for ln in block:
            if not in_sip:
                kv = KV_RE.match(ln)
                if kv and kv.group('k').strip() == 'Sip Message':
                    rec['sip_first'] = kv.group('v').strip()
                    in_sip = True
                elif kv:
                    rec['meta'][kv.group('k').strip()] = kv.group('v').strip()
            else:
                rec['sip'].append(ln)
        recs.append(rec)
    return ver, recs


def classify(rec):
    first = rec['sip_first'] or ''
    if first.startswith('SIP/2.0'):
        return 'response', None, first
    toks = first.split()
    method = toks[0] if toks else '?'
    req_uri = toks[1] if len(toks) > 1 else None
    return 'request', method, req_uri


def digest(path, kst=True):
    ver, recs = parse_capture(path)
    off = datetime.timedelta(hours=9) if kst else datetime.timedelta()
    tz = 'KST' if kst else 'UTC'

    def tfmt(ts):
        return (ts + off).strftime('%m-%d %H:%M:%S.%f')[:-3] if ts else '?'

    reg_reqs, reg_results = {}, {}
    invite_offers, others = [], {}
    span = [r['ts'] for r in recs if r['ts']]
    for r in recs:
        kind, method, uri = classify(r)
        direction = r['meta'].get('Direction', '')
        msgid = r['meta'].get('Message ID', '')
        if kind == 'request' and method == 'REGISTER':
            auth = hdr_val(r['sip'], 'Authorization') or ''
            ad = dict(AUTH_RE.findall(auth))
            key = (uri, hdr_val(r['sip'], 'Expires'),
                   hdr_val(r['sip'], 'User-Agent'),
                   ad.get('username'), ad.get('realm'))
            reg_reqs.setdefault(key, [0, r['ts']])[0] += 1
        elif kind == 'response' and 'REGISTER' in msgid:
            code = r['typeres'].split('/')[-1]
            reason = hdr_val(r['sip'], 'Reason') or ''
            cause = ''
            cm = re.search(r'cause=(\d+)', reason)
            if cm:
                cause = 'cause ' + cm.group(1)
            reg_results.setdefault((code, cause), 0)
            reg_results[(code, cause)] += 1
        elif kind == 'request' and method == 'INVITE' and direction == 'UE_TO_NETWORK':
            sdp = summarize_sdp(r['sip'])
            invite_offers.append({
                'ts': tfmt(r['ts']),
                'session_expires': hdr_val(r['sip'], 'Session-Expires'),
                **sdp})
        elif kind == 'request':
            others[method] = others.get(method, 0) + 1

    out = []
    out.append('## %s   (%s)' % (path.replace('\\', '/').split('/')[-1], ver))
    if span:
        out.append('0x156E packets: %d | span(%s): %s ~ %s'
                   % (len(recs), tz, tfmt(min(span)), tfmt(max(span))))
    # REGISTER requests
    observed = {}
    if reg_reqs:
        out.append('\n### REGISTER - requests (UE->NW)  [distinct]')
        out.append('| %s | req-URI | Expires | User-Agent | Auth username | realm | x |' % tz)
        out.append('|---|---|---|---|---|---|---|')
        for (uri, exp, ua, user, realm), (cnt, ts) in reg_reqs.items():
            out.append('| %s | %s | %s | %s | %s | %s | %d |'
                       % (tfmt(ts), uri, exp, ua, user, realm, cnt))
        # first distinct -> observed.register
        (uri, exp, ua, user, realm), _ = next(iter(reg_reqs.items()))
        observed['register'] = {'req_uri': uri, 'expires': exp, 'user_agent': ua,
                                'auth_username': user, 'realm': realm}
    if reg_results:
        out.append('\n### REGISTER - results (NW->UE)')
        out.append(' ; '.join('%s %s x%d' % (c, ca, n)
                              for (c, ca), n in sorted(reg_results.items())))
        observed['register_results'] = {('%s %s' % (c, ca)).strip(): n
                                        for (c, ca), n in reg_results.items()}
    # INVITE offers
    if invite_offers:
        out.append('\n### INVITE - offers (UE->NW, SDP)')
        out.append('| %s | Session-Expires | audio:port | audio codecs | video codec | res@fps | video:port |' % tz)
        out.append('|---|---|---|---|---|---|---|')
        for o in invite_offers:
            rf = (o['video_res'] or '') + (('@' + o['framerate']) if o['framerate'] else '')
            out.append('| %s | %s | %s | %s | %s | %s | %s |'
                       % (o['ts'], o['session_expires'], o['audio_port'],
                          o['audio_codecs'], o['video_codecs'], rf, o['video_port']))
        f = invite_offers[0]
        observed['invite'] = {k: f.get(k) for k in
                              ('session_expires', 'audio_port', 'audio_codecs',
                               'video_codecs', 'video_res', 'framerate', 'video_port')}
    if others:
        out.append('\n### other requests: ' +
                   ', '.join('%s x%d' % (k, v) for k, v in others.items()))
    return '\n'.join(out), observed


def diff_expected(observed, expected):
    rows = ['\n### expected vs observed', '| field | expected | observed | verdict |',
            '|---|---|---|---|']
    def walk(prefix, exp):
        for k, v in exp.items():
            ov = observed.get(prefix, {}).get(k) if prefix else observed.get(k)
            ev = str(v)
            verdict = '? n/a' if ov is None else (
                'PASS' if (ev == str(ov) or ev in str(ov)) else 'MISMATCH')
            rows.append('| %s.%s | %s | %s | %s |' % (prefix or '-', k, ev, ov, verdict))
    for sect, fields in expected.items():
        if isinstance(fields, dict):
            walk(sect, fields)
        else:
            ov = observed.get(sect)
            rows.append('| %s | %s | %s | %s |' % (sect, fields, ov,
                        'PASS' if str(fields) == str(ov) else 'MISMATCH'))
    return '\n'.join(rows)


def digest_qshrink(path, kst=True):
    """Parse QCAT 0x1FEB/0x1FFB QShrink text (RILQ imsRadio) -> IMS registration
    timeline. The decoded debug lines carry NO inline timestamp, so each
    onRegistrationChanged event is stamped with the most recent 0x1F?B packet header.
    Recovers registration state/errorCode (NOT on-wire SDP override values)."""
    off = datetime.timedelta(hours=9) if kst else datetime.timedelta()
    tz = 'KST' if kst else 'UTC'

    def tfmt(ts):
        return (ts + off).strftime('%m-%d %H:%M:%S.%f')[:-3] if ts else '?'

    last_ts, npkt, span = None, 0, []
    events = []   # (ts, state, ec, rat, uris)
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for ln in fh:
            h = QSH_TS_RE.match(ln)
            if h:
                last_ts = parse_ts(h.group('ts'))
                npkt += 1
                if last_ts:
                    span.append(last_ts)
                continue
            m = REGCHG_RE.search(ln)
            if m:
                ec = m.group('ec')
                events.append((last_ts, m.group('state'),
                               '-' if ec == INT_MAX else ec,
                               (m.group('emsg') or '').strip(),
                               (m.group('rat') or '').strip(),
                               (m.group('uris') or '').strip()))

    # collapse consecutive identical (state, ec) keeping first ts
    timeline = []
    for ts, st, ec, emsg, rat, uris in events:
        if timeline and timeline[-1][1] == st and timeline[-1][2] == ec:
            continue
        timeline.append((ts, st, ec, emsg, rat, uris))

    out = ['## %s   (QShrink imsRadio - 0x1FEB)' % path.replace('\\', '/').split('/')[-1]]
    if span:
        out.append('0x1F?B packets: %d | span(%s): %s ~ %s | regChange events: %d'
                   % (npkt, tz, tfmt(min(span)), tfmt(max(span)), len(events)))
    observed = {}
    if timeline:
        out.append('\n### IMS registration transitions (onRegistrationChanged)')
        out.append('| %s | state | errorCode | errorMessage | radioTech |' % tz)
        out.append('|---|---|---|---|---|')
        for ts, st, ec, emsg, rat, uris in timeline:
            out.append('| %s | %s | %s | %s | %s |'
                       % (tfmt(ts), st, ec, emsg or '-', rat))
        ecs = sorted({(ec, emsg) for _, _, ec, emsg, _, _ in timeline if ec not in ('-', '0')})
        observed = {
            'registered_reached': any(st == 'REGISTERED' for _, st, _, _, _, _ in timeline),
            'final_state': timeline[-1][1],
            'final_errorCode': timeline[-1][2],
            'error_codes': ecs,
        }
        out.append('\n**summary**: REGISTERED reached=%s | final=%s(ec %s) | non-zero error codes=%s'
                   % (observed['registered_reached'], observed['final_state'],
                      observed['final_errorCode'], ecs or 'none'))
    else:
        out.append('\n(no onRegistrationChanged events found - check 0x1FEB decode / .qdb co-location)')
    return '\n'.join(out), observed


def detect_mode(path):
    """Peek file to pick parser: 0x156E SIP text vs 0x1FEB QShrink imsRadio text."""
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for i, ln in enumerate(fh):
            if '0x156E' in ln and 'IMS SIP Message' in ln:
                return 'sip'
            if '0x1FEB' in ln or '0x1FFB' in ln or 'imsRadiolog' in ln:
                return 'qshrink'
            if i > 4000:
                break
    return 'sip'


def main():
    ap = argparse.ArgumentParser(description='QCAT 0x156E SIP text -> verification digest')
    ap.add_argument('files', nargs='+',
                    help='QCAT text file(s): 0x156E SIP and/or 0x1FEB QShrink (auto-detected)')
    ap.add_argument('--utc', action='store_true', help='keep UTC (default: convert to KST)')
    ap.add_argument('--mode', choices=['auto', 'sip', 'qshrink'], default='auto',
                    help='parser mode (default auto-detect per file)')
    ap.add_argument('--json', help='write machine observed object (last file) to this path')
    ap.add_argument('--expected', help='JSON of intended TC values to diff against')
    args = ap.parse_args()
    exp = None
    if args.expected:
        with open(args.expected, encoding='utf-8') as fh:
            exp = json.load(fh)
    last_obs = {}
    for p in args.files:
        mode = args.mode if args.mode != 'auto' else detect_mode(p)
        if mode == 'qshrink':
            md, observed = digest_qshrink(p, kst=not args.utc)
        else:
            md, observed = digest(p, kst=not args.utc)
        print(md)
        if exp:
            # expected may be {capture_basename: {...}} or a flat dict
            base = p.replace('\\', '/').split('/')[-1]
            e = exp.get(base, exp if 'register' in exp or 'invite' in exp else None)
            if e:
                print(diff_expected(observed, e))
        print()
        last_obs = observed
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(last_obs, fh, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
