package main

import (
	"embed"
	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"log"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	app := NewApp()
	err := wails.Run(&options.App{
		Title: "Postroom", Width: 1440, Height: 900, MinWidth: 980, MinHeight: 640,
		BackgroundColour: options.NewRGB(13, 17, 23),
		AssetServer:      &assetserver.Options{Assets: assets},
		OnStartup:        app.startup, OnShutdown: app.shutdown, Bind: []interface{}{app},
	})
	if err != nil {
		log.Fatal(err)
	}
}
