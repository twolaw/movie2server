#!/usr/bin/env python
# coding: utf-8

# puisque Radarr ne sait pas gérer les films dans un unique répertoire, le post-processing est fait à la main
# par un script perso (recup.sh) qui rapatrie le film en bonne place sur le HTPC.

# objectif de ce script déclenché par recup.sh : créer le dossier du film et à l'intérieur un symlink du fichier
# et dire à Radarr de considérer ce film comme téléchargé et à ne plus monitorer via son API

# arguments : 1. final_filename_with_path, fichier d'origine qui sert à créer le symlink
#             2. torrent_hash, pour retrouver le film correspondant dans radarr
#             3. id radarr du film, optionnel, pour forcer manuellement
# exemple : radarr.py "/media/tera/films/Once.Upon.a.Time.2019.1080p.x264.AC3-NoTag.mkv" "332EF42968398534129D0C4E433521D0B8D38316" [id]

# 15-aout-2019 v1.0
# 27           v1.1 resoud bug symlink avec movie_file_nopath
# 15-sept-2019 v1.2 compatible python3 (py2_encode)
# 12-octo-2019 v1.3 rescan placé en dernier car put monitored=false marche pas

host = "192.168.0.4"
port = "7878"
apikey = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" #apikey de radarr

import os, sys, subprocess, json, datetime

PY2 = sys.version_info[0] == 2  # True for Python 2

def py2_encode(s, encoding='utf-8'):
    if PY2:
        s = s.encode(encoding)
    return s

def py2_decode(s, encoding='utf-8'):
    if PY2:
        s = s.decode(encoding)
    return s

root_url = "http://{}:{}/radarr/api/".format(host, port)
movie_file = py2_decode(sys.argv[1])
movie_hash = sys.argv[2]
movie_id = False
if len(sys.argv) > 3:
        movie_id = int(sys.argv[3])
        print("film numero: " + str(movie_id) + " pas besoin de recup l'historique")


if PY2:
        #python2
        from urllib2 import Request, urlopen
        from urllib import urlencode
else:
        #python3
        from urllib.request import Request, urlopen
        from urllib.parse import urlencode

class PutRequest(Request):
        '''class to handling putting with urllib'''
        def get_method(self, *args, **kwargs):
                return 'PUT'

def get_history():
        url_arg = {
                'page': 1,
                'pageSize': 10,
                'apikey': apikey
        }
        req = Request(root_url+"history/?"+urlencode(url_arg))
        response = urlopen(req).read()
        return response
        
def get_movie(movie_num):
        url_arg = {
                'apikey': apikey
        }
        req = Request(root_url+"movie/"+movie_num+"?"+urlencode(url_arg))
        response = urlopen(req).read()
        return response

def rescan_movie(movie_num, movie_title):
        url_arg = {
                'apikey': apikey
        }
        command_data = {
                "name": "RescanMovie",
                "movieId": movie_num
        }
        req = Request(root_url+"command?"+urlencode(url_arg), json.dumps(command_data, ensure_ascii=False))
        req.get_method = lambda: 'POST'
        req.add_header('Content-Type', 'application/json')
        response = urlopen(req).read()
        return response
        
def put_movie(data):
        url_arg = {
                'apikey': apikey
        }
        req = Request(root_url+"movie?"+urlencode(url_arg), py2_encode(json.dumps(data, ensure_ascii=False)))
        req.get_method = lambda: 'PUT'
        req.add_header('Content-Type', 'application/json')
        response = urlopen(req).read()
        return response
                
# si besoin je récupère l'historique des films que Radarr a envoyé à rtorrent pour retrouver l'id corresp
if not movie_id:
        print("radarr.py : transmission a radarr de " + py2_encode(movie_file))
        hist = json.loads(get_history())["records"]
        #print("historique radarr recupere, contient " + str(len(hist)) + " lignes")
        # je cherche le numéro de film correspondant à notre film
        for movie in hist:
                if movie["downloadId"] == movie_hash and movie["eventType"] == "grabbed": # trouvé!
                        movie_id = movie["movieId"]
                        #size = movie["data"]["size"]
                        print("film correspondant (torrent hash=" + movie_hash + ") trouve dans radarr, id=" + str(movie_id))
# si j'ai un id de film correspondant dans radarr, je maj radarr
if movie_id:
        movie_file_nopath = movie_file.split("/").pop()
        movie_data = json.loads(get_movie(str(movie_id)))
        print("donnees radarr du film [" + py2_encode(movie_data["title"]) + "] bien recuperees")
        if not os.path.exists(movie_data['path']):
                os.mkdir(movie_data['path'])
        if not os.path.islink(movie_data['path'] + '/' + movie_file_nopath):
                os.symlink(movie_file, movie_data['path'] + '/' + movie_file_nopath)
                print("lien symbolique cree : " + py2_encode(movie_data['path']) + "/" + py2_encode(movie_file_nopath))
        #je le passe en non-monitored (on ne cherche plus à le telecharger)
        movie_data["monitored"] = False
        #et je renvoie les données à Radarr
        resp = put_movie(movie_data)
        #puis radarr scanne le rep pour trouver le fichier
        cmd_resp = json.loads(rescan_movie(movie_id, movie_data['title']))
        print("monitored=False envoye, commande de rescan du film envoyee a radarr, command id=" + str(cmd_resp['id']))
else:
        print("film introuvable dans radarr avec le hash torrent")
        