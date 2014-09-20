#! /usr/bin/env python
# Publite2 is a process manager which launches multiple Freeciv-web servers
# depending on demand reported by the Metaserver. 

from os import *

import sys
import time
import http.client
import configparser
from pubstatus import *
from civlauncher import Civlauncher
import os.path

metahost = "localhost:8080"
metapath =  "/meta/metaserver.php"
statuspath =  "/meta/status.php"
settings_file = "settings.ini"
game_types = ["singleplayer", "multiplayer"]

metachecker_interval = 60
port = 6000

# The Metachecker class connects to the Freeciv-web metaserver, gets the number of available
# Freeciv-web server instances, and launches new servers if needed.
class metachecker():
    def __init__(self):
      self.server_list = []
      if not os.path.isfile(settings_file):
        print("ERROR: Publite2 isn't setup correctly. Copy settings.ini.dist to settings.ini " +
              "and update it do match your system.")
        sys.exit(1)
      settings = configparser.ConfigParser()
      settings.read(settings_file)
      self.server_capacity = int(settings["Resource usage"]["server_capacity"])
      self.server_limit = int(settings["Resource usage"]["server_limit"])
      self.savesdir = settings["Config"]["save_directory"]
      self.check_count = 0;
      self.total = 0;
      self.single = 0;
      self.multi = 0;
      self.html_doc = "-";
      self.last_http_status = -1;
      s = PubStatus(self)
      s.start();

    def check(self, port):
      while 1:
        try:
          time.sleep(1);
          conn = http.client.HTTPConnection(metahost);
          conn.request("GET", statuspath);
          r1 = conn.getresponse();
          self.check_count += 1;
          self.last_http_status = r1.status;
          if (r1.status == 200):
            self.html_doc = r1.read()
            meta_status = self.html_doc.decode('ascii').split(";");
            if (len(meta_status) == 4):
              self.total = int(meta_status[1]);
              self.single = int(meta_status[2]);
              self.multi = int(meta_status[3]);

              fork_bomb_preventer = (self.total == 0 and self.server_limit < len(self.server_list))
              if fork_bomb_preventer:
                print("Error: Have tried to start more than " + str(self.server_limit)
                      + " servers (the server limit) but according to the"
                      + " metaserver it has found none.");

              while (self.single < self.server_capacity
                     and self.total <= self.server_limit
                     and not fork_bomb_preventer):
                time.sleep(1)
                new_server = Civlauncher(game_types[0], port, metahost + metapath, self.savesdir);
                self.server_list.append(new_server);
                new_server.start();
                port += 1;
                self.total += 1;
                self.single += 1;
 
              while (self.multi < self.server_capacity
                     and self.total <= self.server_limit
                     and not fork_bomb_preventer):
                time.sleep(1)
                new_server = Civlauncher(game_types[1], port, metahost + metapath, self.savesdir)
                self.server_list.append(new_server);
                new_server.start();
                port += 1;
                self.total += 1;
                self.multi += 1;
          else:
            print("Error: Invalid metaserver status");

        except Exception as e:
          self.html_doc = ("Error: Publite2 is unable to connect to Freeciv-web metaserver on http://" + 
                          metahost + metapath + ", error" + str(e));
          print(self.html_doc);
        finally:
          conn.close();
          time.sleep(metachecker_interval);


if __name__ == '__main__':
  #perform a test-request to the Metaserver
  try:
    conn = http.client.HTTPConnection(metahost);
    conn.request("GET", statuspath);
    r1 = conn.getresponse();
  except Exception as e:
    print("Error: Publite2 is unable to connect to Freeciv-web metaserver on http://" 
          + metahost + metapath + ", error" + str(e));
    sys.exit(1)
  finally:
    conn.close();
  
  # start the initial Freeciv-web servers
  mc = metachecker()
  for type in game_types:
    for srv_num in range(mc.server_capacity):
      new_server = Civlauncher(type, port, metahost + metapath, mc.savesdir)
      mc.server_list.append(new_server);
      new_server.start();
      port += 1;

  print("Publite2 started!");
  time.sleep(20);
  mc.check(port);
