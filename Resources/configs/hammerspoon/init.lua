hs.window.filter.new("Ghostty"):subscribe(hs.window.filter.windowFocused, function()
	hs.eventtap.keyStroke({ "cmd", "alt" }, "h")
end)
