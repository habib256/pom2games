// bench — runs the chess engine alone on the POM2 core and counts 6502 cycles.
//
//   bench --bin B --lbl L perft        legal-move count (perft 1) per position
//   bench --bin B --lbl L best [N]     move chosen by the first N levels (FAST,
//                                      STRONG, DEEP; default 2) + cycles
//   bench --bin B --lbl L undo         AI move then undo_last_move restores all
//   bench --bin B --lbl L play N [L]   AI-vs-AI games of up to N plies, L levels
//   bench --bin B --lbl L prof FEN S   cycles per routine for one ai_play_move
//
// B is the engine linked with bench.s (bench_entry at $6000), L its ld65 -Ln
// label file. Each call patches the JSR at bench_entry, points the soft-reset
// vector ($03F2) at it, presses RESET and steps until bench_done: the II+ ROM
// does the rest. Output is plain text, so two engine builds compare by diff
// (the cycle counts aside).
#include <pom2/core.hpp>

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::map<std::string, unsigned> sym;
std::map<unsigned, std::string> byAddr;
std::map<std::string, unsigned long long> prof;
bool profiling = false;

unsigned S(const std::string& name)
{
    auto it = sym.find(name);
    if (it == sym.end()) {
        std::fprintf(stderr, "no symbol %s\n", name.c_str());
        std::exit(1);
    }
    return it->second;
}

const char* kLevel[] = {"FAST  ", "STRONG", "DEEP  "};   // ai_strategy 0, 1, 2

const char* kFens[] = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "rnbqkb1r/pp1p1ppp/4pn2/2p5/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq c6 0 4",
    "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
    "4k3/1P6/8/8/8/8/6p1/4K3 w - - 0 1",
    "8/8/3k4/8/2pP4/8/8/4K3 b - d3 0 1",
};

class Bench {
public:
    explicit Bench(const std::string& roms, const std::string& bin)
    {
        if (!core_.loadRom(roms + "/apple2p.rom")) {
            std::fprintf(stderr, "rom: %s\n", core_.lastError().c_str());
            std::exit(1);
        }
        std::ifstream f(bin, std::ios::binary);
        std::vector<char> data((std::istreambuf_iterator<char>(f)), {});
        if (data.empty()) {
            std::fprintf(stderr, "cannot read %s\n", bin.c_str());
            std::exit(1);
        }
        for (size_t i = 0; i < data.size(); ++i)
            core_.write(static_cast<std::uint16_t>(0x6000 + i), static_cast<std::uint8_t>(data[i]));
    }

    std::uint8_t peek(unsigned a) { return core_.read(static_cast<std::uint16_t>(a)); }
    void poke(unsigned a, unsigned v) { core_.write(static_cast<std::uint16_t>(a), static_cast<std::uint8_t>(v)); }
    std::uint8_t var(const std::string& n) { return peek(S(n)); }
    void set(const std::string& n, unsigned v) { poke(S(n), v); }

    // Runs routine `name`; returns its cycle count. A lands in bench_a.
    unsigned long long call(const std::string& name)
    {
        const unsigned entry = S("bench_entry"), done = S("bench_done"), target = S(name);
        poke(entry + 1, target & 0xFF);
        poke(entry + 2, target >> 8);
        poke(0x3F2, entry & 0xFF);
        poke(0x3F3, entry >> 8);
        poke(0x3F4, (entry >> 8) ^ 0xA5);
        core_.softReset();
        for (long n = 0; core_.cpuState().programCounter != entry; ++n) {
            if (n > 1000000) { std::fprintf(stderr, "reset never reached bench_entry\n"); std::exit(1); }
            core_.step();
        }
        const unsigned long long start = core_.cpuState().cycles;
        unsigned long long last = start;
        for (;;) {
            const pom2::CpuState st = core_.cpuState();
            if (st.programCounter == done) break;
            if (st.cycles - start > 1500000000ULL) { std::fprintf(stderr, "%s never returned (PC=%04X)\n", name.c_str(), st.programCounter); std::exit(1); }
            core_.step();
            if (profiling) {
                auto it = byAddr.upper_bound(st.programCounter);
                const std::string& label = it == byAddr.begin() ? "?" : std::prev(it)->second;
                const unsigned long long now = core_.cpuState().cycles;
                prof[label] += now - last;
                last = now;
            }
        }
        return core_.cpuState().cycles - start;
    }

    void setFen(const std::string& fen)
    {
        std::istringstream in(fen);
        std::string placement, side, castle, ep;
        int half = 0, full = 1;
        in >> placement >> side >> castle >> ep >> half >> full;
        const unsigned board = S("board");
        for (unsigned i = 0; i < 128; ++i) poke(board + i, 0);
        int rank = 7, file = 0;
        for (char c : placement) {
            if (c == '/') { --rank; file = 0; continue; }
            if (c >= '1' && c <= '8') { file += c - '0'; continue; }
            static const std::string kinds = "pnbrqk";
            const unsigned type = static_cast<unsigned>(kinds.find(static_cast<char>(std::tolower(c)))) + 1;
            const unsigned color = std::islower(c) ? 0x80 : 0;
            const unsigned sq = static_cast<unsigned>(rank * 16 + file);
            poke(board + sq, type | color);
            if (type == 6) set(color ? "king_sq_black" : "king_sq_white", sq);
            ++file;
        }
        set("side_to_move", side == "b" ? 0x80 : 0);
        unsigned cr = 0;
        for (char c : castle) cr |= c == 'K' ? 1 : c == 'Q' ? 2 : c == 'k' ? 4 : c == 'q' ? 8 : 0;
        set("castling_rights", cr);
        set("ep_square", ep == "-" ? 0x88 : static_cast<unsigned>((ep[1] - '1') * 16 + (ep[0] - 'a')));
        set("halfmove_clock", static_cast<unsigned>(half));
        set("fullmove_number", static_cast<unsigned>(full));
        set("undo_avail", 0);
        set("ai_rng", 0xAC);
        call("mat_recount");
    }

    // The engine caches both king squares: do they match the board?
    bool kingsOk()
    {
        return peek(S("board") + var("king_sq_white")) == 6 && peek(S("board") + var("king_sq_black")) == 0x86;
    }

    // The engine keeps running material totals: do they match the board?
    bool materialOk()
    {
        static const unsigned value[8] = {0, 1, 3, 3, 5, 9, 0, 0};
        unsigned tot[2] = {0, 0};
        for (unsigned sq = 0; sq < 128; ++sq) {
            const unsigned p = peek(S("board") + sq);
            if (!(sq & 0x88) && p) tot[p >> 7] += value[p & 7];
        }
        return peek(S("mat_tot")) == (tot[0] & 0xFF) && peek(S("mat_tot") + 1) == (tot[1] & 0xFF);
    }

    std::string fen()
    {
        std::string out;
        for (int rank = 7; rank >= 0; --rank) {
            int empty = 0;
            for (int file = 0; file < 8; ++file) {
                const unsigned p = peek(S("board") + static_cast<unsigned>(rank * 16 + file));
                if (!p) { ++empty; continue; }
                if (empty) { out += static_cast<char>('0' + empty); empty = 0; }
                const char c = " pnbrqk?"[p & 7];
                out += (p & 0x80) ? c : static_cast<char>(std::toupper(c));
            }
            if (empty) out += static_cast<char>('0' + empty);
            if (rank) out += '/';
        }
        return out + (var("side_to_move") ? " b" : " w");
    }

private:
    pom2::Core core_;
};

std::string sq(unsigned s)
{
    if (s & 0x88) return "--";
    return std::string(1, static_cast<char>('a' + (s & 7))) + static_cast<char>('1' + (s >> 4));
}

void loadLabels(const std::string& path)
{
    std::ifstream f(path);
    std::string al, addr, name;
    while (f >> al >> addr >> name) {
        if (name[0] == '.') name = name.substr(1);
        const unsigned a = std::strtoul(addr.c_str(), nullptr, 16);
        sym[name] = a;
        if (a >= 0x6000 && name.find("__") != 0 && name[0] != '@') byAddr[a] = name;
    }
}

} // namespace

int main(int argc, char** argv)
{
    std::string exe = argv[0];
    std::string roms = exe.substr(0, exe.rfind('/') + 1) + "../../dev/tools/a2shot/roms";
    std::string bin, lbl;
    std::vector<std::string> args;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--roms" && i + 1 < argc) roms = argv[++i];
        else if (a == "--bin" && i + 1 < argc) bin = argv[++i];
        else if (a == "--lbl" && i + 1 < argc) lbl = argv[++i];
        else args.push_back(a);
    }
    if (bin.empty() || lbl.empty() || args.empty()) {
        std::fprintf(stderr, "usage: bench --bin B --lbl L perft | best [N] | undo | play N [L] | prof FEN STRATEGY\n");
        return 2;
    }
    loadLabels(lbl);
    Bench b(roms, bin);
    const std::string& cmd = args[0];

    if (cmd == "perft") {
        for (const char* fen : kFens) {
            b.setFen(fen);
            const unsigned long long cy = b.call("perft1");
            const unsigned n = b.var("perft_count_lo") | b.var("perft_count_hi") << 8;
            b.setFen(fen);
            b.call("game_status");
            std::printf("perft1 %3u  status %u  %9llu cy  %s\n", n, b.var("bench_a"), cy, fen);
        }
    } else if (cmd == "best") {
        const unsigned levels = args.size() > 1 ? static_cast<unsigned>(std::atoi(args[1].c_str())) : 2;
        unsigned long long total[3] = {0, 0, 0};
        for (const char* fen : kFens) {
            std::printf("%s\n", fen);
            for (unsigned strat = 0; strat < levels; ++strat) {
                b.setFen(fen);
                b.set("ai_strategy", strat);
                const unsigned long long cy = b.call("ai_play_move");
                total[strat] += cy;
                const bool none = b.var("bench_p") & 1;
                std::printf("  %s %s%s  %10llu cy (%.2f s)\n", kLevel[strat],
                            none ? "none" : sq(b.var("ai_best_from")).c_str(),
                            none ? "" : sq(b.var("ai_best_to")).c_str(), cy, cy / 1020484.0);
            }
        }
        std::printf("total");
        for (unsigned strat = 0; strat < levels; ++strat)
            std::printf("  %s %llu cy (%.1f s)", kLevel[strat], total[strat], total[strat] / 1020484.0);
        std::printf("\n");
    } else if (cmd == "undo") {
        // Play the AI move then undo it: board and material must come back.
        for (const char* fen : kFens) {
            b.setFen(fen);
            const std::string before = b.fen();
            b.set("ai_strategy", 0);
            b.call("ai_play_move");
            const std::string move = sq(b.var("ai_best_from")) + sq(b.var("ai_best_to"));
            b.call("undo_last_move");
            const bool ok = b.fen() == before && b.materialOk() && b.kingsOk();
            std::printf("%s %s  %s\n", ok ? "ok  " : "FAIL", move.c_str(), fen);
        }
    } else if (cmd == "play") {
        const int plies = args.size() > 1 ? std::atoi(args[1].c_str()) : 40;
        const unsigned levels = args.size() > 2 ? static_cast<unsigned>(std::atoi(args[2].c_str())) : 2;
        unsigned long long total = 0;
        for (unsigned strat = 0; strat < levels; ++strat) {
            for (unsigned seed : {0xACu, 0x31u, 0x77u}) {
                b.setFen(kFens[0]);
                b.set("ai_strategy", strat);
                b.set("ai_rng", seed);
                std::printf("%s seed %02X:", kLevel[strat], seed);
                for (int p = 0; p < plies; ++p) {
                    b.call("game_status");
                    if (b.var("bench_a")) { std::printf(" [status %u]", b.var("bench_a")); break; }
                    total += b.call("ai_play_move");
                    if (b.var("bench_p") & 1) {
                        std::printf(" [no move: best %s%s flags %02X err %u]", sq(b.var("ai_best_from")).c_str(),
                                    sq(b.var("ai_best_to")).c_str(), b.var("ai_best_flags"), b.var("bench_a"));
                        std::printf("\n  %s  kings %s %s", b.fen().c_str(), sq(b.var("king_sq_white")).c_str(),
                                    sq(b.var("king_sq_black")).c_str());
                        break;
                    }
                    std::printf(" %s%s", sq(b.var("ai_best_from")).c_str(), sq(b.var("ai_best_to")).c_str());
                    if (!b.materialOk()) std::printf(" [material %u %u]", b.peek(S("mat_tot")), b.peek(S("mat_tot") + 1));
                    if (!b.kingsOk()) std::printf(" [king cache %s %s]", sq(b.var("king_sq_white")).c_str(),
                                                  sq(b.var("king_sq_black")).c_str());
                }
                std::printf("\n");
            }
        }
        std::printf("total ai_play_move %llu cy (%.1f s)\n", total, total / 1020484.0);
    } else if (cmd == "prof" && args.size() > 2) {
        b.setFen(args[1]);
        b.set("ai_strategy", static_cast<unsigned>(std::atoi(args[2].c_str())));
        profiling = true;
        const unsigned long long cy = b.call("ai_play_move");
        std::vector<std::pair<unsigned long long, std::string>> rows;
        for (auto& [k, v] : prof) rows.push_back({v, k});
        std::sort(rows.rbegin(), rows.rend());
        std::printf("%llu cycles (%.2f s)\n", cy, cy / 1020484.0);
        for (auto& [v, k] : rows) std::printf("%5.1f%%  %s\n", 100.0 * v / cy, k.c_str());
    } else {
        std::fprintf(stderr, "unknown command %s\n", cmd.c_str());
        return 2;
    }
    return 0;
}
