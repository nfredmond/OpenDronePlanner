"""Actual custody and packaging checks, with Docker mocked only at its boundary."""
import hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from processing import Processing,filename,ident

class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Processing(Path(self.tmp.name));self.c=self.p.create({'name':'Public test capture','mission':{'name':'Synthetic flight','points':[]}});self.id=self.c['id']
 def upload(self,name='photo.jpg',data=b'original image bytes'):
  return self.p.upload(self.id,name,0,len(data),io.BytesIO(data),len(data))
 def test_chunked_original_and_manifest(self):
  self.p.upload(self.id,'photo.jpg',0,6,io.BytesIO(b'abc'),3)
  self.assertEqual(self.p.read(self.id)['files'],[])
  result=self.p.upload(self.id,'photo.jpg',3,6,io.BytesIO(b'def'),3)
  self.assertEqual(result['file']['sha256'],hashlib.sha256(b'abcdef').hexdigest())
  self.assertEqual((self.p.capture_path(self.id)/'media/photo.jpg').read_bytes(),b'abcdef')
  self.assertEqual(self.p.captures()[0]['mission']['name'],'Synthetic flight')
 def test_reject_path_size_offset_and_duplicate(self):
  for bad in ['../a.jpg','a\\b.jpg','a\n.jpg','a".jpg']:
   with self.assertRaisesRegex(ValueError,'file name'):self.upload(bad)
  with self.assertRaises(ValueError):self.p.read('../secret')
  with self.assertRaisesRegex(ValueError,'size'):self.p.upload(self.id,'x.jpg',0,2,io.BytesIO(b'abc'),3)
  with self.assertRaisesRegex(ValueError,'offset'):self.p.upload(self.id,'x.jpg',1,3,io.BytesIO(b'bc'),2)
  self.p.upload(self.id,'x.jpg',0,6,io.BytesIO(b'abc'),3)
  with self.assertRaisesRegex(ValueError,'offset'):self.p.upload(self.id,'x.jpg',2,6,io.BytesIO(b'de'),2)
  self.upload()
  with self.assertRaisesRegex(ValueError,'already exists'):self.upload('PHOTO.JPG',b'changed')
  self.assertEqual((self.p.capture_path(self.id)/'media/photo.jpg').read_bytes(),b'original image bytes')
 def test_disk_headroom_and_partial_input(self):
  with patch('processing.shutil.disk_usage',return_value=type('Usage',(),{'free':100})()):
   with self.assertRaisesRegex(ValueError,'1 GB'):self.upload()
  with self.assertRaisesRegex(ValueError,'interrupted'):self.p.upload(self.id,'a.jpg',0,10,io.BytesIO(b'abc'),10)
  self.assertEqual(self.p.read(self.id)['files'],[])
 def test_report_escape_and_delivery_contents(self):
  self.upload();self.p.notes({'id':self.id,'findings':'<script>alert(1)</script>','client':'A & B'})
  report=self.p.report(self.id).decode();self.assertNotIn('<script>',report);self.assertIn('&lt;script&gt;',report);self.assertIn('A &amp; B',report)
  with zipfile.ZipFile(io.BytesIO(self.p.package(self.id))) as z:
   self.assertEqual(set(z.namelist()),{'report.html','capture-manifest.json','flight.odp.json','README.txt'})
   self.assertEqual(json.loads(z.read('capture-manifest.json'))['files'][0]['sha256'],hashlib.sha256(b'original image bytes').hexdigest())
 def test_portable_cpu_and_explicit_cuda(self):
  cpu=self.p.compose_config('cpu',8888);gpu=self.p.compose_config('cuda',8888)
  self.assertNotIn('gpus',cpu['services']['node-odx-1']);self.assertEqual(gpu['services']['node-odx-1']['gpus'],'all')
  self.assertEqual(cpu['services']['webapp']['ports'],['127.0.0.1:8888:8000'])
  self.assertTrue(all(v['restart']=='no' for v in cpu['services'].values()))
 def test_failed_gpu_probe_does_not_claim_ready(self):
  def command(args,*a,**kw):
   if args[0]=='run':raise ValueError('No GPU runtime')
   return ''
  with patch.object(self.p,'command',side_effect=command):
   with self.assertRaisesRegex(ValueError,'CUDA is unavailable'):self.p.start({'mode':'cuda'})
  self.assertFalse(self.p.ready);self.assertFalse(self.p.engine_lock.locked())
 def test_integrity_blocks_webodm_commit(self):
  self.upload('1.jpg');self.upload('2.jpg');self.p.ready=True
  (self.p.capture_path(self.id)/'media/2.jpg').write_bytes(b'changed')
  def api(path,body=None):
   if path=='projects/':return {'id':1}
   if path=='projects/1/tasks/':return {'id':'task'}
   self.fail('Commit reached despite changed file')
  with patch.object(self.p,'options',return_value=[{'name':'max-concurrency'}]),patch.object(self.p,'api',side_effect=api),patch.object(self.p,'send_file') as send:
   with self.assertRaisesRegex(ValueError,'changed on disk'):self.p.submit({'id':self.id,'preset':'custom'})
  self.assertEqual(send.call_count,1);self.assertEqual(self.p.read(self.id)['runs'][0]['status'],'Upload failed');self.assertFalse(self.p.busy.is_set())
 def test_unsupported_options_block_submission(self):
  self.upload('1.jpg');self.upload('2.jpg');self.p.ready=True
  with patch.object(self.p,'options',return_value=[{'name':'max-concurrency'}]),patch.object(self.p,'api') as api:
   with self.assertRaisesRegex(ValueError,'not supported'):self.p.submit({'id':self.id,'preset':'custom','options':{'invented':True}})
   api.assert_not_called()
 def test_active_includes_jobs_created_in_full_webodm(self):
  self.p.ready=True
  with patch.object(self.p,'api',side_effect=[[{'id':77}],[{'partial':False,'status':20}]]):self.assertTrue(self.p.active())
  with patch.object(self.p,'api',side_effect=[[{'id':77}],[{'partial':True,'status':None},{'partial':False,'status':40}]]):self.assertFalse(self.p.active())

if __name__=='__main__':unittest.main()
