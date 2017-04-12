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



def get_id(mstr):
	#print(mstr)
	return int(mstr[mstr.find("/",1)+1:])

def parse_song_page(songid):
	if CrawlerCore.check_xiami_song(songid):
		return True

	title,albumId,artistId,downurl=xiami.get_song_full_info(str(songid))
	print("Song:"+title)

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
	

	CrawlerCore.enqueue_album(albumId)
	CrawlerCore.enqueue_artist(artistId)

	CrawlerCore.register_song(songid,downurl)
	return False


def parse_album_page(albumid):
	if CrawlerCore.check_xiami_album(albumid):
		return
	tree = etree.parse("http://www.xiami.com/song/playlist/id/%d/type/1" % albumid)
	#获取xml的根节点
	root = tree.getroot()

	#下面用来获取歌曲信息
	albumName =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:album_name',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
	print ("album:"+albumName)#![CDATA[ 为爱而生 ]]
	artist = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:artistId',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
	album_logo = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:album_logo',namespaces={"xm": 'http://xspf.org/ns/0/'})
	songs =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:songId',namespaces={"xm": 'http://xspf.org/ns/0/'})
	songslist = [0] * len(songs)
	for i in range(len(songs)):
		songslist[i]=int(songs[i].text)
		#write song-album pair
		CrawlerCore.enqueue_song(songslist[i])
	#write album and album-artist pair 
	CrawlerCore.register_album(albumid)

def parse_artist_page(artistid):
	if CrawlerCore.check_xiami_artist(artistid):
		return
	tree = etree.parse("http://www.xiami.com/song/playlist/id/%d/type/2" % artistid)
	#获取xml的根节点
	root = tree.getroot()

	#下面用来获取歌曲信息
	artistName = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:singers',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
	print ("artist:"+artistName)
	songs =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:songId',namespaces={"xm": 'http://xspf.org/ns/0/'})
	songslist = [0] * len(songs)
	for i in range(len(songs)):
		songslist[i]=int(songs[i].text)
		CrawlerCore.enqueue_song(songslist[i])
	#write album and album-artist pair 
	CrawlerCore.register_artist(artistid)

def worker():
	while True:
		if CrawlerCore.is_canceled: 
			return
		try:
			task = CrawlerCore.dequeue()
			if task[0]==0:
				should_redo=parse_song_page(task[1])
				CrawlerCore.done_song(task[1])
				if should_redo:
					continue
			elif  task[0]==1:
				parse_album_page(task[1])
				CrawlerCore.done_album(task[1])		
			elif  task[0]==2:
				parse_artist_page(task[1])
				CrawlerCore.done_artist(task[1])
		except Exception as e:
			sys.stderr.write(e.__doc__+"\n")
			sys.stderr.write(e.message+"\n")
		else:
			time.sleep(4.5)