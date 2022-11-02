# xlwings Server: GitHub Issues Dashboard

![Screenshot](/screenshot.png?raw=true)

This sample works with:

* Google Sheets

## Configuration

* For local development: copy `.env.template` to `.env` and provide your values
* For deployment: set the key/value pairs from `.env` as environment variables

## Server

* Local: install the dependencies via `pip install -r requirements.txt` and run the server locally via `python run.py`
* Docker: run `docker compose up`

## Client

* Google Sheets template: https://docs.google.com/spreadsheets/d/1QqCObh12zDL-fOvKFbFnXBCO-wHqrrVvwaxUjmd3Kuo/template/preview
* Once you've copied the template, click on `Extensions` > `Apps Scripts` and replace `URL` with the actual URL of your server
* Fill in a repo name in the form `owner/repo`, then hit the refresh button

## Render

For a 1-click deployment to render.com, click here:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)