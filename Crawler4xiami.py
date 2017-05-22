#!/usr/bin/python
# -*- coding: utf-8 -*-
import xiami
import CrawlerCore

import urllib
import urllib2
from lxml import etree
import lxml
import time
import requests
import sys
import HTMLParser
import json

import MySQLdb
import traceback



h = HTMLParser.HTMLParser()
def get_id(mstr):
	#print(mstr)
	return int(mstr[mstr.find("/",1)+1:])

def html2str(lyc):
	for i in range(len(lyc)):
		if lyc[i]!=' ' and lyc[i]!='\n' and lyc[i]!='\t' and ord(lyc[i])!=13:
	 		lyc=lyc[i:]
	 		break
	lyc=lyc.replace("<br/>","\n")
	lyc=lyc.replace("</div>","")
	lyc=lyc.replace("</strong>","")
	lyc=lyc.replace("<strong>","")	
	return lyc

def sqlwrite_batch(db,command,data):
	try:
		cursor = db.cursor()
		cursor.executemany(command,data)		
		db.commit()
	except MySQLdb.IntegrityError as e:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback,limit=None, file=sys.stderr)
		if e.args[0] != 1062:
			return False
	except Exception as e:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback,limit=None, file=sys.stderr)
		return False
	finally:
		cursor.close()
	return True

def sqlwrite(db,command,data):
	try:
		cursor = db.cursor()
		cursor.execute(command,data)		
		db.commit()
	except MySQLdb.IntegrityError as e:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback,limit=None, file=sys.stderr)
		if e.args[0] != 1062:
			return False
	except Exception as e:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback,limit=None, file=sys.stderr)
		return False
	finally:
		cursor.close()
	return True

def parse_song_page(db,songid):
	if CrawlerCore.check_xiami_song(songid):
		return 1

	title,albumId,artistId,downurl=xiami.get_song_full_info(str(songid))

	session = requests.Session()
	session.headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
	}
	session.get('https://xiami.com')
	xmlUrl="http://www.xiami.com/song/"+str(songid)
	htmltext = session.get(xmlUrl).text
	tree = etree.HTML( htmltext);
	elem=tree.find("./body/div[@id=\"page\"]/div[@id=\"wrapper\"]/div[@id=\"content\"]/div[@id=\"main_wrapper\"]/div[@id=\"sidebar\"]/div[@id=\"relate_song\"]")
	if elem is not None:
		elem=elem.xpath(".//td[@class=\"song_name\"]")
		for i in elem:
			node= i.find("./p/a")
			sid=get_id(node.attrib['href'])
			CrawlerCore.enqueue_song(sid)
	else:
		sys.stderr.write("song %d no related songs\n" % songid)
	
	url2="http://www.xiami.com/count/getplaycount?id=%d&type=song"%songid
	htmltext = session.get(url2).text
	data=json.loads(htmltext)
	play_cnt=0
	if data["status"]=="ok":
		play_cnt=int(data["plays"])
	else:
		sys.stderr.write("song %d no playcount\n" % songid)


	elem=tree.find('.//ul[@class="clearfix"]/li/a[@href="#wall"]')
	comment_cnt=0
	if elem is not None:
		tex=elem.text
		comment_cnt=int(tex)
	else:
		sys.stderr.write("song %d no commentcount\n" % songid)

	elem=tree.find(".//div[@class=\"lrc_main\"]")
	lyc=""
	if elem is not None:
		lyc=etree.tostring(elem)
		if "&#" in lyc:
			lyc=h.unescape(lyc)
		lyc=html2str(lyc[lyc.find(">")+1:])
	else:
		sys.stderr.write("song %d no lyc\n" % songid)

	print ("Song: %s, play= %d , comment= %d" % (title,play_cnt,comment_cnt))
	CrawlerCore.enqueue_album(albumId)
	CrawlerCore.enqueue_artist(artistId)

	if not sqlwrite(db,"insert into music_artist(music_id,artist_id) values(%s,%s)",(songid,artistId)):
		return 2
	
	if not sqlwrite(db,"insert into music(id,name,lyc,play_cnt,comment_cnt) values(%s,%s,%s,%s,%s)",(songid,title,lyc,play_cnt,comment_cnt)):
		return 2
	CrawlerCore.register_song(songid,play_cnt,downurl)
	return 0


def parse_album_page(db,albumid):
	if CrawlerCore.check_xiami_album(albumid):
		return
	albumName=""
	artist=""
	album_logo=""
	songslist = []
	if False:
		tree = etree.parse("http://www.xiami.com/song/playlist/id/%d/type/1" % albumid)
		#获取xml的根节点
		root = tree.getroot()

		#下面用来获取歌曲信息
		albumName =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:album_name',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
		artist = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:artistId',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
		album_logo = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:album_logo',namespaces={"xm": 'http://xspf.org/ns/0/'})
		songs =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:songId',namespaces={"xm": 'http://xspf.org/ns/0/'})
		songslist = [0] * len(songs)
		for i in range(len(songs)):
			songslist[i]=(int(songs[i].text),albumid,i+1)
			#write song-album pair
			CrawlerCore.enqueue_song(songslist[i][0])

	session = requests.Session()
	session.headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
	}
	session.get('https://xiami.com')
	xmlUrl="http://www.xiami.com/album/"+str(albumid)
	htmltext = session.get(xmlUrl).text
	tree = etree.HTML( htmltext);
	elem=tree.find(".//span[@property=\"v:summary\"]/p")
	des=""
	if elem is not None:
		des=h.unescape(etree.tostring(elem))
		des=html2str(des[des.find(">")+1:])
	else:
		elem=tree.find('.//span[@property="v:summary"]')
		if elem is not None:
			des=h.unescape(etree.tostring(elem))
			des=html2str(des[des.find(">")+1:])
		else:
			sys.stderr.write("album %d no description\n" % albumid)
	elem=tree.find(".//em[@id=\"play_count_num\"]")
	play_cnt=0
	if elem is not None:
		tex= etree.tostring(elem)
		tex= tex[tex.find(">")+1:]
		tail=tex.find("<")
		if tail!=-1:
			tex= tex[:tail-1]
		play_cnt=int(tex)
	else:
		sys.stderr.write("album %d no playcount\n" % albumid)
	elem=tree.find(".//i[@property=\"v:count\"]")
	comment_cnt=0
	if elem is not None:
		tex=elem.text
		comment_cnt=int(tex)
	else:
		sys.stderr.write("album %d no commentcount\n" % albumid)

	elem=tree.find('.//div[@id="album_cover"]/a/img')
	picurl=""
	if elem is not None:
		picurl= elem.attrib["src"]
	else:
		sys.stderr.write("album %d no photo\n" % albumid)

	elem=tree.find('.//div[@id="title"]/h1')
	albumName=""
	if elem is not None:
		albumName=elem.text
		print albumName
	else:
		raise BaseException
	xmlUrl2="http://www.xiami.com/song/playlist/id/%d/type/1" % albumid
	htmltext = session.get(xmlUrl2).text
	cur= htmltext.find("<songId>")
	track_id=0
	while cur != -1:
		track_id+=1
		end = htmltext.find("</songId>",cur)
		if end==-1 :
			break
		strid=htmltext[cur+len("<songId>"):end]
		songslist.append( (int(strid),albumid,track_id) )
		cur=htmltext.find("<songId>",end)

	print ("album: %s, play= %d , comment= %d" % (albumName,play_cnt,comment_cnt))
	#write album and album-artist pair
	if not sqlwrite(db,"insert into album(id,name,description,pic,play_cnt,comment_cnt) values(%s,%s,%s,%s,%s,%s)",(albumid,albumName,des,picurl,play_cnt,comment_cnt)):
		return 2
	if not sqlwrite_batch(db,"insert into music_album (music_id,album_id,morder) values(%s,%s,%s)",songslist):
		return 2
	if not sqlwrite(db,"insert into album_artist (artist_id,album_id) values(%s,%s)",(int(artist),albumid)):
		return 2	
	CrawlerCore.register_album(albumid)
	return 0

def parse_artist_page(db,artistid):
	if CrawlerCore.check_xiami_artist(artistid):
		return
	if False:
		tree = etree.parse("http://www.xiami.com/song/playlist/id/%d/type/2" % artistid)
		#获取xml的根节点
		root = tree.getroot()

		#下面用来获取歌曲信息
	
		artistName = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:singers',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
		songs =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:songId',namespaces={"xm": 'http://xspf.org/ns/0/'})
		songslist = [0] * len(songs)
		for i in range(min(len(songs),30)):
			songslist[i]=int(songs[i].text)
			CrawlerCore.enqueue_song(songslist[i])

	session = requests.Session()
	session.headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
	}
	session.get('https://xiami.com')
	xmlUrl="http://www.xiami.com/artist/"+str(artistid)
	htmltext = session.get(xmlUrl).text
	tree = etree.HTML( htmltext);
	elem=tree.find(".//div[@class=\"record\"]")
	des=""
	if elem is not None:
		des=h.unescape(etree.tostring(elem))
		des=html2str(des[des.find(">")+1:])
	else:
		sys.stderr.write("artist %d no description\n" % artistid)
	elem=tree.find('.//ul[@class="clearfix"]/li/a[@href="#wall"]')
	comment_cnt=0
	if elem is not None:
		tex=elem.text
		comment_cnt=int(tex)
	else:
		sys.stderr.write("artist %d no commentcount\n" % artistid)
	elem=tree.find('.//div[@id="artist_photo"]/a/img')
	picurl=""
	if elem is not None:
		picurl= elem.attrib["src"]
	else:
		sys.stderr.write("artist %d no photo\n" % albumid)
	elem=tree.find('.//div[@id="title"]/h1')
	artistName=""
	if elem is not None:
		artistName=elem.text
		print artistName
	else:
		raise BaseException
	#use json to get the count
	url2="http://www.xiami.com/count/getplaycount?id=%d&type=artist"%artistid
	htmltext = session.get(url2).text
	data=json.loads(htmltext)
	play_cnt=0
	if data["status"]=="ok":
		play_cnt=int(data["plays"])
	else:
		sys.stderr.write("artist %d no playcount\n" % artistid)
	print ("artist: %s, play= %d , comment= %d" % (artistName,play_cnt,comment_cnt))
	if not sqlwrite(db,"insert into artist(id,name,description,pic,play_cnt,comment_cnt) values(%s,%s,%s,%s,%s,%s)",(artistid,artistName,des,picurl,play_cnt,comment_cnt)):
		return 2
	CrawlerCore.register_artist(artistid)
	return 1

def worker():
	db = MySQLdb.connect("localhost","root","thisismysql","mistmusic")
	db.set_character_set('utf8')
	print("Open MySQL ok")
	err_cnt=0
	cycle_num=0
	while True:
		if CrawlerCore.is_canceled: 
			return
		cycle_num+=1
		if cycle_num == 10:
			if err_cnt>=9:
				print "too many errors, now sleep"
				time.sleep(240)
			else:
				time.sleep(10)
			cycle_num=0
			err_cnt=0
		if CrawlerCore.is_canceled: 
			return
		task=0
		try:
			task = CrawlerCore.dequeue()
			if task[0]==0:
				ret=parse_song_page(db,task[1])
				if ret!=2:
					CrawlerCore.done_song(task[1])
				if ret==1:
					continue
			elif  task[0]==1:
				ret=parse_album_page(db,task[1])
				if ret!=2:
					CrawlerCore.done_album(task[1])	
			elif  task[0]==2:
				ret=parse_artist_page(db,task[1])
				if ret!=2:
					CrawlerCore.done_artist(task[1])
			elif  task[0]==-1:
				return
			elif  task[0]==-2:
				continue
		except Exception as e:
			err_cnt+=1
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_exception(exc_type, exc_value, exc_traceback,limit=None, file=sys.stderr)
			CrawlerCore.bad_task(task)
		finally:
			CrawlerCore.done_task(task)
		time.sleep(5)
	db.close()	


def aaa():
	session = requests.Session()
	session.headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
	}
	session.get('https://xiami.com')
	xmlUrl="http://www.xiami.com/song/1769167647"
	htmltext = session.get(xmlUrl).text
	tree = etree.HTML( htmltext);
	elem=tree.find(".//div[@class=\"lrc_main\"]")
	lyc=""
	if elem is not None:
		lyc=etree.tostring(elem)
		
		if "&#" in lyc:
			lyc=h.unescape(lyc)
		print lyc
		lyc=html2str(lyc[lyc.find(">")+1:])
		print lyc
	else:
		sys.stderr.write("song %d no lyc\n" % songid)

def parse_album_page2(albumid):
	session = requests.Session()
	session.headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
	}
	session.get('https://xiami.com')
	xmlUrl="http://www.xiami.com/album/"+str(albumid)
	htmltext = session.get(xmlUrl).text
	tree = etree.HTML( htmltext);

	elem=tree.find('.//div[@id="title"]/h1')
	albumName=""
	if elem is not None:
		albumName=elem.text
		print albumName
	else:
		raise BaseException
	xmlUrl2="http://www.xiami.com/song/playlist/id/%d/type/1" % albumid
	htmltext = session.get(xmlUrl2).text
	cur= htmltext.find("<songId>")
	while cur != -1:
		end = htmltext.find("</songId>",cur)
		if end==-1 :
			break
		strid=htmltext[cur+len("<songId>"):end]
		print strid
		cur=htmltext.find("<songId>",end)
	#print ("album: %s, play= %d , comment= %d" % (albumName,play_cnt,comment_cnt))


def artist_test(artistid):
	session = requests.Session()
	session.headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
	}
	session.get('https://xiami.com')
	xmlUrl="http://www.xiami.com/artist/"+str(artistid)
	htmltext = session.get(xmlUrl).text
	tree = etree.HTML( htmltext);
	elem=tree.find(".//div[@class=\"record\"]")
	des=""
	if elem is not None:
		des=h.unescape(etree.tostring(elem))
		des=html2str(des[des.find(">")+1:])
	else:
		sys.stderr.write("artist %d no description\n" % artistid)
	elem=tree.find('.//ul[@class="clearfix"]/li/a[@href="#wall"]')
	comment_cnt=0
	if elem is not None:
		tex=elem.text
		comment_cnt=int(tex)
	else:
		sys.stderr.write("artist %d no commentcount\n" % artistid)
	elem=tree.find('.//div[@id="artist_photo"]/a/img')
	picurl=""
	if elem is not None:
		picurl= elem.attrib["src"]
	else:
		sys.stderr.write("artist %d no photo\n" % albumid)
	url2="http://www.xiami.com/count/getplaycount?id=%d&type=artist"%artistid
	htmltext = session.get(url2).text
	data=json.loads(htmltext)
	play_cnt=0
	if data["status"]=="ok":
		play_cnt=int(data["plays"])
	else:
		sys.stderr.write("artist %d no playcount\n" % artistid)

#aaa()
#parse_album_page2(421981)
#artist_test(3110)
