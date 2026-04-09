--[[ Clean Mode - Work-Friendly Playlist Generator
     Part of rockbox-explicit-filter
     https://github.com/Tyal13/rockbox-explicit-filter

     Reads pre-generated clean playlist and starts shuffle playback.
     Run the Python tagger with --playlists to generate the M3U files.
]]

require("actions")
require("playlist")

local CLEAN_PLAYLIST = "/.rockbox/playlists/clean_library.m3u8"
local CANCEL_BUTTON = rb.actions.PLA_CANCEL

-- Simple menu using splash messages and button input
local function show_menu()
    local items = {
        "Shuffle Clean Library",
        "Play Clean (In Order)",
        "Cancel"
    }
    local selected = 1

    while true do
        -- Show current selection
        rb.splash(0, selected .. "/" .. #items .. ": " .. items[selected])

        local action = rb.get_plugin_action(-1)

        if action == rb.actions.PLA_UP or action == rb.actions.PLA_SCROLL_BACK then
            selected = selected - 1
            if selected < 1 then selected = #items end
        elseif action == rb.actions.PLA_DOWN or action == rb.actions.PLA_SCROLL_FWD then
            selected = selected + 1
            if selected > #items then selected = 1 end
        elseif action == rb.actions.PLA_SELECT then
            return selected
        elseif action == CANCEL_BUTTON then
            return #items
        end
    end
end

-- Check if clean playlist exists
local function file_exists(path)
    local f = io.open(path, "r")
    if f then
        f:close()
        return true
    end
    return false
end

-- Load playlist and count tracks
local function load_clean_playlist(shuffle)
    if not file_exists(CLEAN_PLAYLIST) then
        rb.splash(rb.HZ * 3,
            "Clean playlist not found! Run the tagger with --playlists first.")
        return false
    end

    -- Read track count for display
    local count = 0
    local f = io.open(CLEAN_PLAYLIST, "r")
    if f then
        for line in f:lines() do
            if line:sub(1,1) ~= "#" and line:len() > 3 then
                count = count + 1
            end
        end
        f:close()
    end

    rb.splash(rb.HZ * 2, "Loading " .. count .. " clean tracks...")

    -- Create new playlist from the M3U file
    rb.playlist_remove_all_tracks()
    rb.playlist_create("/", "")

    local f2 = io.open(CLEAN_PLAYLIST, "r")
    if f2 then
        for line in f2:lines() do
            if line:sub(1,1) ~= "#" and line:len() > 3 then
                local path = line
                -- Ensure path starts with /
                if path:sub(1,1) ~= "/" then
                    path = "/" .. path
                end
                rb.playlist_insert_track(path, rb.PLAYLIST_INSERT_LAST, false, false)
            end
        end
        f2:close()
    end

    if shuffle then
        rb.playlist_shuffle(os.time(), 0)
    end

    rb.playlist_start(0, 0, 0)
    rb.splash(rb.HZ * 2, "Clean Mode ON - " .. count .. " tracks")
    return true
end

-- Main
local choice = show_menu()

if choice == 1 then
    load_clean_playlist(true)
elseif choice == 2 then
    load_clean_playlist(false)
end
