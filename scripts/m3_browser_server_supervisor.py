"""CI-only Django web-process crash/restart supervisor for real S3 receipt tests."""
import os
import signal
import subprocess
import sys
from pathlib import Path

marker=os.environ.get('M3_CI_CRASH_MARKER')
if not (marker and os.environ.get('M3_LIVE_S3_CLAMAV')=='1'
        and os.environ.get('M3_S3_ALLOW_LOCAL_TEST_ENDPOINT')=='1'
        and os.environ.get('M3_S3_ENDPOINT_URL')=='http://127.0.0.1:9000'):
    raise SystemExit('Live CI-only loopback environment required')
process=None
def stop(_sig,_frame):
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
cmd=[sys.executable,'manage.py','runserver','--nostatic','--noreload','127.0.0.1:8000']
env=os.environ.copy()
env['M3_CI_CRASH_AFTER_PUT']='1'
process=subprocess.Popen(cmd,env=env)
first=process.wait()
if first!=79:
    raise SystemExit('CI web server exited unexpectedly before the intended S3 crash: '+str(first))
Path(marker).write_text('WEB_EXIT_79_AFTER_REAL_S3_PUT\n')
env.pop('M3_CI_CRASH_AFTER_PUT',None)
process=subprocess.Popen(cmd,env=env)
second=process.wait()
raise SystemExit('Restarted web server exited unexpectedly: '+str(second))
