--[[

Copyright (c) 2014 Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.
See the License for the specific language governing permissions and
limitations under the License.

--]]

-- Read params
local msgset_key = KEYS[1]

local now = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local claim_id = ARGV[3]
local claim_expires = tonumber(ARGV[4])
local msg_ttl = tonumber(ARGV[5])
local msg_expires = tonumber(ARGV[6])

-- Scan for up to 'limit' unclaimed messages
local BATCH_SIZE = 100

local start = 0
local claimed_msgs = {}

local found_unclaimed = false

while (#claimed_msgs < limit) do
    local stop = (start + BATCH_SIZE - 1)
    local msg_ids = redis.call('ZRANGE', msgset_key, start, stop)

    if (#msg_ids == 0) then
        break
    end

    start = start + BATCH_SIZE

    -- TODO(kgriffs): Try moving claimed IDs to a different set
    -- to avoid scanning through already-claimed messages.
    for i, mid in ipairs(msg_ids) do
        -- NOTE(kgriffs): Since execution of this script can not
        -- happen in parallel, once we find the first unclaimed
        -- message, the remaining messages will always be
        -- unclaimed as well.

        if not found_unclaimed then
            local msg = redis.call('HMGET', mid, 'c', 'c.e')

            if msg[1] == '' or tonumber(msg[2]) <= now then
                found_unclaimed = true
            end
        end

        if found_unclaimed then
            local msg_expires_prev = redis.call('HGET', mid, 'e')

            -- Found an unclaimed message, so claim it
            redis.call('HMSET', mid,
                       'c', claim_id,
                       'c.e', claim_expires)

            -- Will the message expire early?
            if tonumber(msg_expires_prev) < claim_expires then
                redis.call('HMSET', mid,
                           't', msg_ttl,
                           'e', msg_expires)
            end

            claimed_msgs[#claimed_msgs + 1] = mid

            if (#claimed_msgs == limit) then
                break
            end
        end
    end
end

return claimed_msgs
