import sys
import Queue
import AtomicCounter
import threading

import os.path


song_id_set=set()
song_id_lock=threading.Lock()

album_id_set=set()
album_id_lock=threading.Lock()

artist_id_set=set()
artist_id_lock=threading.Lock()

file_song_queue=0#open("song_queue.txt","a+")
file_song_queue_head=0#open("song_queue.txt","a+")
artist_file=0
album_file=0

song_queue=Queue.Queue()
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
	global file_song_queue,file_song_queue_head,artist_file,album_file
	myqueue=set()

	artist_file=0
	album_file=0

	if os.path.exists("outdir/queue.txt"):
		file_song_queue=open("outdir/queue.txt","r")
		for line in file_song_queue:
			kv=line.split()
			myqueue.add((int(kv[0]),int(kv[1])))
		file_song_queue.close()

	file_song_queue_head=open("outdir/song.txt","a+")
	for line in file_song_queue_head:
		itm=int(line)
		song_id_set.add(itm)
		if itm in myqueue:
			myqueue.remove( (0,itm) )

	album_file=open("outdir/album.txt","a+")
	for line in album_file:
		itm=int(line)
		album_id_set.add(itm)
		if itm in myqueue:
			myqueue.remove( (1,itm) )

	artist_file=open("outdir/artist.txt","a+")
	for line in artist_file:
		itm=int(line)
		artist_id_set.add(itm)
		if itm in myqueue:
			myqueue.remove( (2,itm) )

	file_song_queue=open("outdir/queue.txt","w")
	for itm in myqueue:
		file_song_queue.write("%d %d\n" % (itm[0],itm[1]))
		song_queue.put(itm)
		working_queue.add(itm)
	file_song_queue.flush()
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
	song_queue.put((0,xiami_id))

def enqueue_song(xiami_id):
	if check_xiami_song(xiami_id):
		return
	with queue_lock:
		if (0,xiami_id) in working_queue:
			return
		working_queue.add((0,xiami_id))
	file_song_queue.write("0 %d\n" % xiami_id)
	file_song_queue.flush()
	song_queue.put((0,xiami_id))

def dequeue():
	return song_queue.get()

def done_song(xiami_id):
	file_song_queue_head.write("%d\n" % xiami_id)
	file_song_queue_head.flush()
	song_queue.task_done()
	with queue_lock:
		if (0,xiami_id) in working_queue:
			working_queue.remove((0,xiami_id))

def join():
	song_queue.join()

def cancel():
	global is_canceled
	is_canceled=True

def enqueue_album(xiami_id):
	if check_xiami_album(xiami_id):
		return
	with queue_lock:
		if (1,xiami_id) in working_queue:
			return
		working_queue.add((1,xiami_id))
	file_song_queue.write("1 %d\n" % xiami_id)
	file_song_queue.flush()
	song_queue.put((1,xiami_id))

def done_album(xiami_id):
	album_file.write("%d\n" % xiami_id)
	album_file.flush()
	song_queue.task_done()
	with queue_lock:
		if (1,xiami_id) in working_queue:
			working_queue.remove((1,xiami_id))

def enqueue_artist(xiami_id):
	if check_xiami_artist(xiami_id):
		return
	with queue_lock:
		if (2,xiami_id) in working_queue:
			return
		working_queue.add((2,xiami_id))
	file_song_queue.write("2 %d\n" % xiami_id)
	file_song_queue.flush()
	song_queue.put((2,xiami_id))

def done_artist(xiami_id):
	artist_file.write("%d\n" % xiami_id)
	artist_file.flush()
	song_queue.task_done()
	with queue_lock:
		if (2,xiami_id) in working_queue:
			working_queue.remove((2,xiami_id))
