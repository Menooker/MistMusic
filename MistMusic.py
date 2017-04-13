#!/usr/bin/python
# -*- coding: utf-8 -*-
import Crawler4xiami
import CrawlerCore
import threading

CrawlerCore.put_song(380246)#小手拉大手
CrawlerCore.put_song(130762)#后来
CrawlerCore.put_song(378181)#爱我别走
CrawlerCore.put_song(1769901638)#Rolling In The Deep
CrawlerCore.put_song(2067242)#好久不见
#CrawlerCore.put_song(1769938907)#An Der Schönen Blauen Donau Op.314
threads=[]
for i in range(5):
     t = threading.Thread(target=Crawler4xiami.worker)
     threads.append(t)
     t.daemon = True
     t.start()

while True:
	inp=raw_input()
	if inp=="e":
		break

print("Canceled")
CrawlerCore.cancel()
for t in threads:
	t.join()
