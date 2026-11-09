import datetime as dt
import json
import unittest
from fetch_snow import collect, station_observation, JST

STATION={'code':'48141','name':'白馬','alt':703,'km':2.8}
LATEST=dt.datetime(2026,12,10,6,10,tzinfo=JST)

class SnowTests(unittest.TestCase):
    def observation(self, values):
        return station_observation('48141', STATION, LATEST,
            lambda url: json.dumps({'20261210060000':values}))

    def test_snow(self):
        s=self.observation({'temp':[-5.2,0],'snow':[85,0],'snow24h':[12,0]})
        self.assertEqual((s['snow'],s['snow24h'],s['temp']),(85,12,-5.2))
        self.assertEqual(s['observedAt'],'2026-12-10T06:00:00+09:00')

    def test_missing_fields(self):
        s=self.observation({'temp':[4.1,0]})
        self.assertIsNone(s['snow']);self.assertIsNone(s['snow24h'])

    def test_bad_flag(self):
        s=self.observation({'temp':[4,1],'snow':[85,2],'snow24h':[0,0]})
        self.assertIsNone(s['temp']);self.assertIsNone(s['snow']);self.assertEqual(s['snow24h'],0)

    def test_fallback(self):
        urls=[]
        def getter(url):
            urls.append(url)
            return '{}' if len(urls)==1 else json.dumps({'20261210055000':{'temp':[1,0]}})
        s=station_observation('48141',STATION,LATEST,getter)
        self.assertIn('20261210_03.json',urls[1]);self.assertIn('05:50',s['observedAt'])

    def test_partial_failure_and_dedup(self):
        urls=[]
        def getter(url):
            urls.append(url)
            if url.endswith('.txt'):return LATEST.isoformat()
            if '/bad/' in url:raise OSError('offline')
            return json.dumps({'20261210060000':{'temp':[-5,0],'snow':[85,0],'snow24h':[12,0]}})
        data=collect([{'amedas':STATION},{'amedas':STATION},{'amedas':{**STATION,'code':'bad'}}],getter)
        self.assertIsNone(data['stations']['bad']);self.assertTrue(data['season'])
        self.assertEqual(data['headline']['text'],'過去 24 小時降雪最多：白馬 12 cm')
        self.assertEqual(len(urls),3)

    def test_no_snow_and_depth_headline(self):
        for values,season,text in [({'temp':[4,0]},False,'各觀測站目前還沒有積雪紀錄'),({'temp':[0,0],'snow':[2,0]},True,'目前積雪最深：白馬 2 cm')]:
            data=collect([{'amedas':STATION}],lambda url:LATEST.isoformat() if url.endswith('.txt') else json.dumps({'20261210060000':values}))
            self.assertEqual(data['season'],season);self.assertEqual(data['headline']['text'],text)

    def test_all_fail(self):
        def getter(url):
            if url.endswith('.txt'):return LATEST.isoformat()
            raise OSError('offline')
        with self.assertRaises(RuntimeError):collect([{'amedas':STATION}],getter)

if __name__=='__main__':unittest.main()
