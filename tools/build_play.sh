#!/bin/sh
# Builds play.html (local test copy with a full HTML wrapper) from index.html. Run inside the 七窟_原型 folder.
{ printf '%s' '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><style>:root{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px);box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'; cat index.html; printf '%s' '</body></html>'; } > play.html
