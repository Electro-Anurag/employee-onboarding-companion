"""ClamAV INSTREAM transport. Does not assert antivirus protection without a daemon.

A result is CLEAN only for an exact daemon 'stream: OK' response. Any socket,
protocol, configuration or service error fails closed and is retryable.
"""
import socket
import struct
from django.conf import settings

class ScannerUnavailable(Exception):
    pass

def clamav_scan(payload):
    if not isinstance(payload,bytes) or not 1<=len(payload)<=10*1024*1024:
        raise ScannerUnavailable('INVALID_SCAN_PAYLOAD')
    host=getattr(settings,'M3_CLAMAV_HOST','')
    port=getattr(settings,'M3_CLAMAV_PORT',3310)
    if not host or not isinstance(port,int) or not 1<=port<=65535:
        raise ScannerUnavailable('SCANNER_NOT_CONFIGURED')
    try:
        with socket.create_connection((host,port),timeout=2) as stream:
            stream.settimeout(2)
            stream.sendall(b'zINSTREAM\\0'.replace(b'\\0',b'\0'))
            for offset in range(0,len(payload),65536):
                block=payload[offset:offset+65536]
                stream.sendall(struct.pack('!I',len(block))+block)
            stream.sendall(struct.pack('!I',0))
            result=bytearray()
            while len(result)<=512:
                chunk=stream.recv(513-len(result))
                if not chunk:break
                result.extend(chunk)
                if b'\0' in result or b'\n' in result:break
            if len(result)>512 or not result:
                raise ScannerUnavailable('INVALID_SCANNER_RESPONSE')
            output=bytes(result).rstrip(b'\r\n\0')
            if output==b'stream: OK':
                return 'CLEAN','ClamAV INSTREAM clean response'
            if output.startswith(b'stream: ') and output.endswith(b' FOUND'):
                return 'MALWARE','ClamAV reports malware'
            raise ScannerUnavailable('SCANNER_INDETERMINATE')
    except (OSError,TimeoutError) as exc:
        raise ScannerUnavailable('SCANNER_UNAVAILABLE') from exc

def clamav_signature_provenance():
    """Live clamd VERSION response and ≤48-hour signature database freshness.

    Any missing/unparseable/outdated signature date prevents a CLEAN result.
    This check is required on the real worker path (not deterministic test
    doubles); a successful INSTREAM verdict alone is insufficient.
    """
    import re
    from datetime import datetime,timezone as tz,timedelta
    host=getattr(settings,'M3_CLAMAV_HOST','')
    port=getattr(settings,'M3_CLAMAV_PORT',3310)
    if not host:raise ScannerUnavailable('SCANNER_NOT_CONFIGURED')
    try:
        with socket.create_connection((host,port),timeout=2) as stream:
            stream.settimeout(2)
            stream.sendall(b'zVERSION\0')
            result=bytearray()
            while len(result)<256:
                part=stream.recv(256-len(result))
                if not part:break
                result.extend(part)
                if b'\0' in part or b'\n' in part:break
    except OSError as exc:
        raise ScannerUnavailable('SCANNER_VERSION_UNAVAILABLE') from exc
    answer=bytes(result).rstrip(b'\r\n\0').decode('ascii','replace')
    # Real clamd VERSION response: ClamAV X.Y.Z/DB_VERSION/Tue Oct 9 00:00:00 2026
    parts=answer.split('/')
    if len(parts)!=3 or not parts[0].startswith('ClamAV ') or not parts[1].isdigit():
        raise ScannerUnavailable('INVALID_SCANNER_VERSION')
    try:
        stamp=datetime.strptime(parts[2],'%a %b %d %H:%M:%S %Y').replace(tzinfo=tz.utc)
    except ValueError as exc:
        raise ScannerUnavailable('INVALID_SIGNATURE_DATE') from exc
    age=datetime.now(tz.utc)-stamp
    if age<timedelta(minutes=-5) or age>timedelta(hours=48):
        raise ScannerUnavailable('STALE_SCANNER_SIGNATURES')
    return answer[:150]
