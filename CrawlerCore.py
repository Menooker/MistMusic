import sys
import Queue
import AtomicCounter
import threading

import os.path
import time

song_id_set=set()
song_id_lock=threading.Lock()

album_id_set=set()
album_id_lock=threading.Lock()

artist_id_set=set()
artist_id_lock=threading.Lock()

file_song_queue=0#open("song_queue.txt","a+")
file_song_queue_head=0#open("song_queue.txt","a+")
file_read_queue=0
artist_file=0
album_file=0

working_queue=set()
count=0
filecount=0
count_lock=threading.Lock()
queue_lock=threading.Lock()
is_canceled=False

from time import gmtime, strftime


out_url_file_time=strftime("%Y%m%d-%H-%M-%S", gmtime())
out_url_file=open("outdir/mp3_url_%s_%d.txt" % (out_url_file_time,0),"w")



def init_cache():
	print("Initializing URL cache...")
	global file_song_queue,file_song_queue_head,artist_file,album_file,file_read_queue
	myqueue=set()

	artist_file=0
	album_file=0

	file_song_queue_head=open("outdir/song.txt","a+")
	for line in file_song_queue_head:
		itm=int(line)
		song_id_set.add(itm)

	album_file=open("outdir/album.txt","a+")
	for line in album_file:
		itm=int(line)
		album_id_set.add(itm)

	artist_file=open("outdir/artist.txt","a+")
	for line in artist_file:
		itm=int(line)
		artist_id_set.add(itm)

	if os.path.exists("outdir/queue.txt"):
		temp_file=open("outdir/queue_tmp.txt","w")
		old_file=open("outdir/queue.txt","r")
		for line in old_file:
			kv=line.split()
			mtype=int(kv[0])
			mid=int(kv[1])
			if mtype==0:
				if mid in song_id_set:
					continue
			elif mtype==1:
				if mid in album_id_set:
					continue
			elif mtype==2:
				if mid in artist_file:
					continue
			temp_file.write(line)
		old_file.close()
		temp_file.close()
		os.remove("outdir/queue.txt")
		os.rename("outdir/queue_tmp.txt","outdir/queue.txt")

	file_song_queue=open("outdir/queue.txt","at")
	file_read_queue=open("outdir/queue.txt","rt")
	file_read_queue.seek(0)
	print("Read cache done")
init_cache()

def register_song(xiami_id,url):
	global out_url_file,out_url_file_time,count,filecount
	#write some DB
	with song_id_lock:
		count+=1
		out_url_file.write("%d %s\n" % (xiami_id,url))
		out_url_file.flush()
		if count % 500==0:
			out_url_file.close()
			filecount+=1
			out_url_file=open("outdir/mp3_url_%s_%d.txt" % (out_url_file_time,filecount),"w")
		song_id_set.add(xiami_id)
		



def check_xiami_song( xiami_id):
	with song_id_lock:
		if xiami_id in song_id_set:
			return True
		return False


def register_album(xiami_id):
	#write some DB
	with album_id_lock:
		album_id_set.add(xiami_id)		


def check_xiami_album(xiami_id):
	with album_id_lock:
		if xiami_id in album_id_set:
			return True
		return False

def check_xiami_artist(xiami_id):
	with artist_id_lock:
		if xiami_id in artist_id_set:
			return True
		return False

def register_artist(xiami_id):
	#write some DB
	with artist_id_lock:
		artist_id_set.add(xiami_id)
	
		


def put_song(xiami_id):
	enqueue_song(xiami_id)

def enqueue_song(xiami_id):
	if check_xiami_song(xiami_id):
		return
	with queue_lock:
		if (0,xiami_id) in working_queue:
			return
		file_song_queue.write("0 %d\n" % xiami_id)
		file_song_queue.flush()
	

def dequeue():
	with queue_lock:
		kv=[]
		while True:
			if is_canceled:
				return (-1,-1)
			line=file_read_queue.readline()
			kv=line.split()
			if len(kv)==2:
				break
			print ("Line is "+line+". Queue may be empty. Now sleep")
			time.sleep(10)
		tsk=(int(kv[0]),int(kv[1]))
		if tsk in working_queue:
			return (-2,0)
		checking=[check_xiami_song,check_xiami_album,check_xiami_artist]
		if checking[tsk[0]](tsk[1]):
			return (-2,0)
		working_queue.add(tsk)
		return tsk

def done_song(xiami_id):
	with queue_lock:
		file_song_queue_head.write("%d\n" % xiami_id)
		file_song_queue_head.flush()	
		if (0,xiami_id) in working_queue:
			working_queue.remove((0,xiami_id))


def cancel():
	global is_canceled
	is_canceled=True

def enqueue_album(xiami_id):
	if check_xiami_album(xiami_id):
		return
	with queue_lock:
		if (1,xiami_id) in working_queue:
			return
		file_song_queue.write("1 %d\n" % xiami_id)
		file_song_queue.flush()

def done_album(xiami_id):
	with queue_lock:
		album_file.write("%d\n" % xiami_id)
		album_file.flush()
		if (1,xiami_id) in working_queue:
			working_queue.remove((1,xiami_id))

def enqueue_artist(xiami_id):
	if check_xiami_artist(xiami_id):
		return
	with queue_lock:
		if (2,xiami_id) in working_queue:
			return
		file_song_queue.write("2 %d\n" % xiami_id)
		file_song_queue.flush()

def done_artist(xiami_id):
	with queue_lock:
		artist_file.write("%d\n" % xiami_id)
		artist_file.flush()
		if (2,xiami_id) in working_queue:
			working_queue.remove((2,xiami_id))
