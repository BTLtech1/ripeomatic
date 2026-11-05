// Host-side tests for the Improv serial framing in firmware/ripeomatic/improv.h.
//   g++ -std=c++17 -Wall -Wextra -I../ripeomatic test_improv.cpp -o test_improv && ./test_improv
#include <cstdio>
#include <cstring>
#include "improv.h"

using namespace improv;
static int failures = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); failures++; } } while (0)

int main() {
  // encode a Wi-Fi settings RPC as the installer would send it
  const char* ssid = "HomeWifi", *pass = "hunter22";
  uint8_t payload[80]; int n = 0;
  payload[n++] = CMD_WIFI_SETTINGS;
  payload[n++] = (uint8_t)(2 + strlen(ssid) + strlen(pass));
  payload[n++] = (uint8_t)strlen(ssid); memcpy(payload + n, ssid, strlen(ssid)); n += strlen(ssid);
  payload[n++] = (uint8_t)strlen(pass); memcpy(payload + n, pass, strlen(pass)); n += strlen(pass);
  uint8_t pkt[300];
  int len = encode(RPC_COMMAND, payload, n, pkt);
  CHECK(len == 6 + 3 + n + 1);
  CHECK(memcmp(pkt, "IMPROV", 6) == 0 && pkt[6] == 1 && pkt[7] == RPC_COMMAND && pkt[8] == n);

  // parse it, with some log noise in front and a partial header to resync past
  Parser p; bool got = false;
  const char* noise = "boot: hello IMPR world ";
  for (const char* c = noise; *c; c++) CHECK(!p.feed((uint8_t)*c));
  for (int i = 0; i < len; i++) { bool r = p.feed(pkt[i]); if (i < len - 1) CHECK(!r); else got = r; }
  CHECK(got);
  CHECK(p.type == RPC_COMMAND && p.len == n);
  char s[33], pw[65];
  CHECK(parseWifiSettings(p.data, p.len, s, sizeof s, pw, sizeof pw));
  CHECK(strcmp(s, ssid) == 0 && strcmp(pw, pass) == 0);

  // a corrupted checksum is rejected, and the parser recovers for the next packet
  pkt[len - 1] ^= 0x55;
  got = false;
  for (int i = 0; i < len; i++) got = p.feed(pkt[i]) || got;
  CHECK(!got);
  pkt[len - 1] ^= 0x55;
  got = false;
  for (int i = 0; i < len; i++) got = p.feed(pkt[i]) || got;
  CHECK(got);

  // open network: empty password
  uint8_t open_[8] = {CMD_WIFI_SETTINGS, 5, 3, 'a', 'b', 'c', 0};
  CHECK(parseWifiSettings(open_, 7, s, sizeof s, pw, sizeof pw) && strcmp(s, "abc") == 0 && pw[0] == 0);
  // truncated payload is rejected
  uint8_t bad[4] = {CMD_WIFI_SETTINGS, 9, 7, 'a'};
  CHECK(!parseWifiSettings(bad, 4, s, sizeof s, pw, sizeof pw));

  // RPC result encoding: command, payload length, length-prefixed strings
  const char* info[] = {"BTL Ripe-O-Matic", "0.1.0", "ESP32", "Ripe-O-Matic a3f9c2"};
  len = encodeResult(CMD_GET_DEVICE_INFO, info, 4, pkt);
  CHECK(pkt[7] == RPC_RESULT);
  CHECK(pkt[9] == CMD_GET_DEVICE_INFO);
  int expect = 0; for (int i = 0; i < 4; i++) expect += 1 + strlen(info[i]);
  CHECK(pkt[10] == expect);
  CHECK(pkt[8] == expect + 2);
  CHECK(pkt[11] == strlen(info[0]) && memcmp(pkt + 12, info[0], strlen(info[0])) == 0);
  // round-trips through the parser
  Parser q; got = false;
  for (int i = 0; i < len; i++) got = q.feed(pkt[i]) || got;
  CHECK(got && q.type == RPC_RESULT && q.len == expect + 2);

  // empty result (end of network list)
  len = encodeResult(CMD_GET_NETWORKS, nullptr, 0, pkt);
  CHECK(len == 6 + 3 + 2 + 1 && pkt[8] == 2 && pkt[10] == 0);

  if (failures) { printf("%d FAILURE(S)\n", failures); return 1; }
  printf("all improv tests passed\n");
  return 0;
}
