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

def parse_song_page(songid):
	if CrawlerCore.check_xiami_song(songid):
		return True

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
	artist = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:artistId',namespaces={"xm": 'http://xspf.org/ns/0/'})[0].text
	album_logo = root.xpath('/xm:playlist/xm:trackList/xm:track/xm:album_logo',namespaces={"xm": 'http://xspf.org/ns/0/'})
	songs =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:songId',namespaces={"xm": 'http://xspf.org/ns/0/'})
	songslist = [0] * len(songs)
	for i in range(len(songs)):
		songslist[i]=int(songs[i].text)
		#write song-album pair
		CrawlerCore.enqueue_song(songslist[i])

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

	print ("album: %s, play= %d , comment= %d" % (albumName,play_cnt,comment_cnt))
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
	songs =  root.xpath('/xm:playlist/xm:trackList/xm:track/xm:songId',namespaces={"xm": 'http://xspf.org/ns/0/'})
	songslist = [0] * len(songs)
	for i in range(len(songs)):
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
			print des
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
		print picurl
	else:
		sys.stderr.write("artist %d no photo\n" % albumid)

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
#parse_album_page2(10061)
#artist_test(3110)