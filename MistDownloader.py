#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
import os
import time
import sys
import traceback

cnt=0
least_cnt=0
if len(sys.argv)==2:
	least_cnt=int(sys.argv[1])
print least_cnt

if not os.path.exists("mp3"):
	os.mkdir("mp3")
for path,dirname,filenames in os.walk("outdir"):
	for filename in filenames:
		if filename.startswith("mp3_url_"):
			cnt+=1
			if cnt%100==0:
				print ("Has already downloaded %d songs!" % cnt)
			f=open("outdir/"+filename)
			for line in f:
				values=line.split()
				if len(values)!=3:
					sys.stderr.write("Bad line '%s' in file %s\n" % (line,filename))
				sid=values[0]
				play_cnt=int(values[1])
				url=values[2]
				if play_cnt<least_cnt:
					continue
				fn="mp3/%s.mp3" % sid
				if not os.path.exists(fn):
					try:
						urllib.urlretrieve(url, fn)
						print(sid)
					except Exception as e:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						traceback.print_exception(exc_type, exc_value, exc_traceback,limit=None, file=sys.stderr)
					time.sleep(2)
			f.close()
