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
local counter_key = KEYS[2]

local num_message_ids = tonumber(ARGV[1])

-- Get next rank value
local rank_counter = tonumber(redis.call('GET', counter_key) or 1)

-- Add ranked message IDs
local zadd_args = {'ZADD', msgset_key}
for i = 0, (num_message_ids - 1) do
    zadd_args[#zadd_args+1] = rank_counter + i
    zadd_args[#zadd_args+1] = ARGV[2 + i]
end

redis.call(unpack(zadd_args))

-- Set next rank value
return redis.call('SET', counter_key, rank_counter + num_message_ids)
