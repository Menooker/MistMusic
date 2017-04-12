import Crawler4xiami
import CrawlerCore
import threading

CrawlerCore.put_song(45808)
CrawlerCore.put_song(380246)

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