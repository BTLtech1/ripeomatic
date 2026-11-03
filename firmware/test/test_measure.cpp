// Host-side tests for firmware/ripeomatic/measure.h.
//   g++ -std=c++17 -Wall -Wextra -I../ripeomatic test_measure.cpp -o test_measure && ./test_measure
// Simulates a blade in series with an avocado and checks that the state
// machine finds contact, preloads, stops at the cap, and recovers the fruit's
// stiffness after the blade correction.
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include "measure.h"

using namespace ripe;

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)
#define CHECK_NEAR(a, b, tol) do { double _a = (a), _b = (b); if (fabs(_a - _b) > (tol)) { printf("FAIL %s:%d  %s = %g, expected %g +- %g\n", __FILE__, __LINE__, #a, _a, _b, (double)(tol)); failures++; } } while (0)

// A virtual machine: sled at pos; fruit surface at fruit_pos; fruit stiffness k_fruit (N/mm);
// blade stiffness k_blade in series. Force from a given sled position solves
// F = k_fruit * squish = k_blade * bend, squish + bend = pos - fruit_pos.
struct Sim {
  float fruit_pos, k_fruit, k_blade, noise;
  unsigned seed = 1;
  float rnd() { seed = seed * 1103515245u + 12345u; return ((seed >> 8) & 0xffff) / 65535.0f - 0.5f; }
  float force(float pos) {
    float pen = pos - fruit_pos;
    if (pen <= 0) return noise * rnd();
    float k = (k_fruit * k_blade) / (k_fruit + k_blade);   // series springs
    if (k_fruit <= 0) k = k_blade;                           // rigid "fruit"
    return k * pen + noise * rnd();
  }
};

static Reading run(MeasureCore& core, Sim& sim, const Tunables& t, float last_contact, int* steps_out = nullptr) {
  core.start(t, last_contact);
  float pos = 0;
  int guard = 0;
  while (true) {
    auto c = core.feed(pos, sim.force(pos));
    if (c.kind == MeasureCore::Cmd::Stop) break;
    pos += c.mm;
    if (++guard > 5000) { printf("runaway\n"); failures++; break; }
  }
  if (steps_out) *steps_out = guard;
  return core.reading();
}

int main() {
  // ---- line fit
  {
    float x[] = {0, 1, 2, 3, 4}, y[] = {1, 3, 5, 7, 9};
    LineFit f = fitLine(x, y, 5);
    CHECK_NEAR(f.slope, 2.0, 1e-5);
    CHECK_NEAR(f.intercept, 1.0, 1e-5);
    CHECK_NEAR(f.r2, 1.0, 1e-6);
    CHECK(fitLine(x, y, 1).n == 1 && fitLine(x, y, 1).slope == 0);
  }

  // ---- a firm avocado, blade correction on, no noise
  {
    Tunables t; t.blade_k_n_per_mm = 3.0f;
    Sim sim{20.0f, 4.0f, 3.0f, 0.0f};
    MeasureCore core;
    int steps;
    Reading r = run(core, sim, t, 0, &steps);
    CHECK(r.outcome == Outcome::Reading);
    CHECK_NEAR(r.contact_pos_mm, 20.0, 0.2);          // 3 consecutive samples above 0.1 N at k=1.71 → ~0.06 mm in + 2 steps
    CHECK(r.force_max_n >= t.force_cap_n);
    CHECK(r.force_max_n < t.force_cap_n + 0.2f);      // one sample step past the cap at most
    CHECK_NEAR(r.stiffness_n_per_mm, 4.0, 0.15);      // blade removed → fruit stiffness
    CHECK(r.r2 > 0.999f);
    CHECK(r.n_points > 10);
    printf("firm: contact %.2f  k %.3f  r2 %.4f  squish@cap %.2f  points %d  steps %d\n",
           r.contact_pos_mm, r.stiffness_n_per_mm, r.r2, r.squish_at_cap_mm, r.n_points, steps);
  }

  // ---- same fruit WITHOUT the blade correction reads softer (series spring), as the docs say
  {
    Tunables t; t.blade_k_n_per_mm = 0;
    Sim sim{20.0f, 4.0f, 3.0f, 0.0f};
    MeasureCore core;
    Reading r = run(core, sim, t, 0);
    CHECK(r.outcome == Outcome::Reading);
    CHECK_NEAR(r.stiffness_n_per_mm, 4.0 * 3.0 / 7.0, 0.1);   // 1.714
  }

  // ---- a ripe avocado, with noise, second run uses last contact → fewer steps
  {
    Tunables t; t.blade_k_n_per_mm = 3.0f;
    Sim sim{23.0f, 1.0f, 3.0f, 0.03f};
    MeasureCore core;
    int s1, s2;
    Reading r1 = run(core, sim, t, 0, &s1);
    Reading r2 = run(core, sim, t, r1.contact_pos_mm, &s2);
    CHECK(r1.outcome == Outcome::Reading && r2.outcome == Outcome::Reading);
    CHECK_NEAR(r1.stiffness_n_per_mm, 1.0, 0.1);
    CHECK_NEAR(r2.stiffness_n_per_mm, 1.0, 0.1);
    CHECK_NEAR(r2.contact_pos_mm, 23.0, 0.3);
    CHECK(r1.force[0] < 0.6f && r2.force[0] < 0.6f);   // first measured point is near the preload, not a slam
    printf("ripe: k %.3f / %.3f  contact %.2f / %.2f  samples %d / %d  first force %.2f / %.2f\n",
           r1.stiffness_n_per_mm, r2.stiffness_n_per_mm, r1.contact_pos_mm, r2.contact_pos_mm, s1, s2, r1.force[0], r2.force[0]);
  }

  // ---- fruit much closer than last time (bigger avocado): approach must not crash through it
  {
    Tunables t; t.blade_k_n_per_mm = 3.0f;
    Sim sim{12.0f, 4.0f, 3.0f, 0.0f};
    MeasureCore core;
    Reading r = run(core, sim, t, 30.0f);   // thinks fruit is at 30, approach would go to 26
    CHECK(r.outcome == Outcome::Reading);
    CHECK_NEAR(r.contact_pos_mm, 12.0, 0.6);   // one approach step (0.5 mm) of overshoot at most
    CHECK(r.force_max_n < t.force_cap_n + 1.0f);
    CHECK_NEAR(r.stiffness_n_per_mm, 4.0, 0.3);
    printf("close fruit: contact %.2f  max force %.2f  k %.3f\n", r.contact_pos_mm, r.force_max_n, r.stiffness_n_per_mm);
  }

  // ---- empty nest
  {
    Tunables t;
    Sim sim{999.0f, 1.0f, 3.0f, 0.02f};
    MeasureCore core;
    Reading r = run(core, sim, t, 25.0f);
    CHECK(r.outcome == Outcome::Empty);
    CHECK(r.n_points == 0);
  }

  // ---- rigid object (blade calibration): slope == blade k
  {
    Tunables t; t.blade_k_n_per_mm = 0;
    Sim sim{18.0f, 0.0f, 3.2f, 0.0f};
    MeasureCore core;
    Reading r = run(core, sim, t, 0);
    CHECK(r.outcome == Outcome::Reading);
    CHECK_NEAR(r.stiffness_n_per_mm, 3.2, 0.05);
  }

  // ---- mush: never reaches the cap
  {
    Tunables t; t.blade_k_n_per_mm = 3.0f;
    Sim sim{20.0f, 0.1f, 3.0f, 0.0f};
    MeasureCore core;
    Reading r = run(core, sim, t, 0);
    CHECK(r.outcome == Outcome::Overtravel);
    CHECK(r.n_points > 0);
  }

  // ---- verdicts
  {
    Tunables t;  // abs 1.5, pct 45
    CHECK(judge(6.0f, 6.0f, t) == Verdict::Hard);
    CHECK(judge(4.0f, 6.0f, t) == Verdict::Firming);
    CHECK(judge(3.0f, 6.0f, t) == Verdict::Nearly);   // thr = max(1.5, 2.7) = 2.7; 3.0 <= 3.51
    CHECK(judge(2.5f, 6.0f, t) == Verdict::Ripe);
    CHECK(judge(1.4f, 0.0f, t) == Verdict::Ripe);     // no first reading: absolute only
    CHECK(judge(0.0f, 6.0f, t) == Verdict::Unknown);
    Tunables off; off.ripe_abs_n_per_mm = 0; off.ripe_pct_of_first = 0;
    CHECK(judge(1.0f, 6.0f, off) == Verdict::Unknown);
  }

  // ---- swap detection
  {
    Tunables t;
    CHECK(looksLikeNewFruit(30.0f, 20.0f, 3.0f, 3.0f, t));        // contact moved 10 mm
    CHECK(!looksLikeNewFruit(21.0f, 20.0f, 2.8f, 3.0f, t));
    CHECK(looksLikeNewFruit(20.5f, 20.0f, 5.0f, 2.0f, t));        // got much stiffer
    CHECK(!looksLikeNewFruit(20.5f, 0.0f, 5.0f, 0.0f, t));        // no history
  }

  // ---- days to ripe
  {
    // 6 → 4 N/mm over 2 days, threshold 2.7: rate = ln(1.5)/2 = 0.2027/day; d = ln(4/2.7)/0.2027 = 1.94
    CHECK_NEAR(daysToRipe(6.0f, 4.0f, 2.0f, 2.7f), 1.94, 0.05);
    CHECK(daysToRipe(6.0f, 6.0f, 2.0f, 2.7f) < 0);
    CHECK(daysToRipe(6.0f, 2.0f, 2.0f, 2.7f) == 0);
    CHECK(daysToRipe(6.0f, 4.0f, 0.1f, 2.7f) < 0);
  }

  // ---- CSV
  {
    Tunables t; t.blade_k_n_per_mm = 3.0f;
    Sim sim{20.0f, 4.0f, 3.0f, 0.0f};
    MeasureCore core;
    Reading r = run(core, sim, t, 0);
    RowMeta m{"a3f9c2", "2026-11-09T07:30:12Z", "a3f9c2-0007", "hass", 182, NAN, "0:0,100:0.98", "", "", "cut open, no bruising"};
    char row[1024];
    int n = formatReadingRow(r, m, t.force_cap_n, row, sizeof row);
    CHECK(n > 0 && n < (int)sizeof row);
    // count columns, respecting quotes
    int cols = 1; bool q = false;
    for (char* p = row; *p; p++) { if (*p == '"') q = !q; else if (*p == ',' && !q) cols++; }
    int hcols = 1; for (const char* p = csvHeader(); *p; p++) if (*p == ',') hcols++;
    CHECK(cols == hcols);
    CHECK(strstr(row, "\"cut open, no bruising\"") != nullptr);
    CHECK(strncmp(row, "1,a3f9c2,", 9) == 0);
    printf("row: %s\n", row);

    RowMeta e{"a3f9c2", "2026-11-09T19:00:00Z", "a3f9c2-0007", "hass", 0, NAN, "", "perfect", "no_bruise", ""};
    n = formatEventRow(e, row, sizeof row);
    cols = 1; q = false;
    for (char* p = row; *p; p++) { if (*p == '"') q = !q; else if (*p == ',' && !q) cols++; }
    CHECK(cols == hcols);
    CHECK(strstr(row, ",perfect,no_bruise,") != nullptr);
    printf("event: %s\n", row);

    char f[32];
    csvField("plain", f, sizeof f); CHECK(strcmp(f, "plain") == 0);
    csvField("a,b", f, sizeof f); CHECK(strcmp(f, "\"a,b\"") == 0);
    csvField("say \"hi\"", f, sizeof f); CHECK(strcmp(f, "\"say \"\"hi\"\"\"") == 0);
  }

  if (failures) { printf("%d FAILURE(S)\n", failures); return 1; }
  printf("all tests passed\n");
  return 0;
}
