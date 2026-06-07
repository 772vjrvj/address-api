1. git pull
2. 가상환경 만들기 python -m venv venv
3. 가상환경 세팅 Project Settings
4. 가상환경 활성화 venv\Scripts\activate


GIT BASH

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~
$ cd C:/Users/772vjrvj/Documents/GitHub

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub
$ git clone https://github.com/772vjrvj/address-api.git
Cloning into 'address-api'...
remote: Enumerating objects: 12, done.
remote: Counting objects: 100% (12/12), done.
remote: Compressing objects: 100% (10/10), done.
remote: Total 12 (delta 1), reused 12 (delta 1), pack-reused 0 (from 0)
Unpacking objects: 100% (12/12), done.

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub
$ cd address-api/

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub/address-api (main)
$ python -m venv venv

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub/address-api (main)
$ source venv/Scripts/activate
(venv)

772vjrvj@DESKTOP-SHRPUN8 MINGW64 ~/Documents/GitHub/address-api (main)
$ pip install -r requirements.txt


touch .env
notepad .env

MASTER_API_KEY=my_secret_master_key_1234!



python run.py