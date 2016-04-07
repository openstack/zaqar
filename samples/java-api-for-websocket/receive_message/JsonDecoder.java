/*
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License.  You may obtain a copy
 * of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package org.openstack.zaqar.sample;

import java.io.StringReader;

import javax.json.Json;
import javax.json.JsonObject;
import javax.websocket.Decoder;
import javax.websocket.EndpointConfig;

public final class JsonDecoder implements Decoder.Text<JsonObject> {

    @Override
    public JsonObject decode(final String s) {
        return Json.createReader(new StringReader(s)).readObject();
    }

    @Override
    public void destroy() {
    }

    @Override
    public void init(final EndpointConfig config) {
    }

    @Override
    public boolean willDecode(final String s) {
        return true;
    }

}