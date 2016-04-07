/*
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License.  You may obtain a copy
 * of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import javax.ws.rs.client.Client;
import javax.ws.rs.client.ClientBuilder;
import javax.ws.rs.client.Entity;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.MultivaluedHashMap;
import javax.ws.rs.core.MultivaluedMap;

@SuppressWarnings("serial")
@WebServlet(name = "SampleZaqarServlet", value = "/")
public final class SampleZaqarServlet extends HttpServlet {

    @Override
    protected void doGet(final HttpServletRequest req,
            final HttpServletResponse resp) {
        final Client client = ClientBuilder.newClient();

        final MultivaluedMap<String, Object> headers =
                new MultivaluedHashMap<String, Object>();

        headers.putSingle("Client-ID", "355186cd-d1e8-4108-a3ac-a2183697232a");

        headers.putSingle("X-Auth-Token", "8444886dd9b04a1b87ddb502b508261c");

        headers.putSingle("X-Project-Id", "7530fad032ca431e9dc8ed4a5de5d99c");

        client.target("http://localhost:8888/v2/queues/SampleQueue/messages")
                .request(MediaType.APPLICATION_JSON_TYPE).headers(headers)
                .post(Entity
                        .json("{\"messages\":[{\"body\":\"Zaqar Sample\"}]}"));

        client.close();
    }

}
