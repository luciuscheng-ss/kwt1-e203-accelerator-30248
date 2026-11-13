// Full-event VCD crop/statistics engine. Input is the exact stream hashed by
// fast_vcd_window.py; no activity signals are filtered from the output.
// V2: token spans, compact timestamp arenas, direct short-code lookup and sticky
// untracked statistics. Native protocol/output semantics match the frozen engine.
// C++11 standard library only.
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

typedef long long Tick;
static const size_t NONE = std::numeric_limits<size_t>::max();
static const Tick NA = -1;

struct Token {
    const char* data; size_t size; bool upper;
    Token():data(NULL),size(0),upper(false){}
};
static bool space_byte(unsigned char c) {return c==' ' || (c>='\t' && c<='\r');}
struct Reader {
    std::vector<char> buffer; size_t position,count; std::string spill;
    Reader():buffer(1024*1024),position(0),count(0){}
    bool refill() {
        count=std::fread(&buffer[0],1,buffer.size(),stdin);position=0;
        if(!count&&std::ferror(stdin))throw std::runtime_error("input stream read failed");
        return count!=0;
    }
    int get() {
        if(position==count&&!refill())return EOF;
        return static_cast<unsigned char>(buffer[position++]);
    }
    bool token(Token& out) {
        spill.clear();out.upper=false;
        for(;;) {
            if(position==count&&!refill())return false;
            while(position<count&&space_byte(static_cast<unsigned char>(buffer[position])))++position;
            if(position<count)break;
        }
        for(;;) {
            size_t begin=position;
            while(position<count&&!space_byte(static_cast<unsigned char>(buffer[position]))) {
                unsigned char c=static_cast<unsigned char>(buffer[position]);
                if(c>127)throw std::runtime_error("non-ASCII byte in VCD body");
                out.upper=out.upper||(c>='A'&&c<='Z');++position;
            }
            size_t length=position-begin;
            if(position<count) {
                if(spill.empty()){out.data=&buffer[begin];out.size=length;}
                else {spill.append(&buffer[begin],length);out.data=spill.data();out.size=spill.size();}
                ++position;return true;
            }
            spill.append(&buffer[begin],length);
            if(!refill()){out.data=spill.data();out.size=spill.size();return true;}
        }
    }
};
static bool equals(const Token& t,const char* text) {
    size_t length=std::strlen(text);return t.size==length&&std::memcmp(t.data,text,length)==0;
}
struct Lookup {
    std::vector<size_t> direct;
    std::unordered_map<uint64_t,size_t> packed;
    std::unordered_map<std::string,size_t> fallback;
    Lookup():direct(839515,NONE){}
    static bool printable(const char* p,size_t n) {
        for(size_t i=0;i<n;++i)if(static_cast<unsigned char>(p[i])<33||static_cast<unsigned char>(p[i])>126)return false;
        return true;
    }
    static size_t short_key(const char* p,size_t n) {
        size_t k=0;for(size_t i=0;i<n;++i)k=k*94+(static_cast<unsigned char>(p[i])-32);return k;
    }
    static uint64_t long_key(const char* p,size_t n) {
        uint64_t k=0;for(size_t i=0;i<n;++i)k|=static_cast<uint64_t>(static_cast<unsigned char>(p[i]))<<(i*8);return k;
    }
    void add(const std::string& code,size_t index) {
        if(code.size()<=3&&printable(code.data(),code.size()))direct[short_key(code.data(),code.size())]=index;
        else if(code.size()<=8&&printable(code.data(),code.size()))packed[long_key(code.data(),code.size())]=index;
        else fallback[code]=index;
    }
    size_t find(const char* p,size_t n)const {
        if(n<=3&&printable(p,n))return direct[short_key(p,n)];
        if(n<=8&&printable(p,n)){std::unordered_map<uint64_t,size_t>::const_iterator i=packed.find(long_key(p,n));return i==packed.end()?NONE:i->second;}
        std::unordered_map<std::string,size_t>::const_iterator i=fallback.find(std::string(p,n));return i==fallback.end()?NONE:i->second;
    }
};

struct Signal {
    std::string code, value, initial, last;
    size_t width;
    bool tracked, present, changed, had_unknown, initial_present, last_present;
    Tick last_time, changes, flips, unknown_ticks, rises, first_rise, last_rise, min_period, max_period;
    Signal(): width(0), tracked(false), present(false), changed(false), had_unknown(false),
        initial_present(false), last_present(false), last_time(0), changes(0), flips(0),
        unknown_ticks(0), rises(0), first_rise(NA), last_rise(NA), min_period(NA), max_period(NA) {}
};
struct Event {
    size_t index,offset,length; int control,mode;
    Event(size_t i,size_t o,size_t n,int c,int m):index(i),offset(o),length(n),control(c),mode(m){}
};

enum { NO_CONTROL=0, DUMPVARS=1, DUMPON=2, DUMPOFF=3, DUMPALL=4 };
static const char* control_name(int n) {
    switch(n) { case DUMPVARS:return "$dumpvars";case DUMPON:return "$dumpon";
        case DUMPOFF:return "$dumpoff";case DUMPALL:return "$dumpall";default:return ""; }
}
static int control_number(const Token& s) {
    if(equals(s,"$dumpvars"))return DUMPVARS;if(equals(s,"$dumpon"))return DUMPON;
    if(equals(s,"$dumpoff"))return DUMPOFF;if(equals(s,"$dumpall"))return DUMPALL;return NO_CONTROL;
}

static bool unknown(const std::string& value) {
    return !value.empty() && value[0]!='r' && value.find_first_of("xz")!=std::string::npos;
}
static std::string bits(const std::string& value, size_t width) {
    if(!value.empty() && value[0]=='r')return std::string();
    std::string raw = !value.empty() && value[0]=='b' ? value.substr(1) : value;
    char fill = !raw.empty() && (raw[0]=='x'||raw[0]=='z') ? raw[0] : '0';
    if(raw.size()<width)raw.insert(0,width-raw.size(),fill);
    return raw;
}
static Tick tick(const Token& s) {
    size_t p=1;bool minus=false;
    if(p<s.size&&(s.data[p]=='+'||s.data[p]=='-')){minus=s.data[p]=='-';++p;}
    if(p==s.size)throw std::runtime_error("invalid VCD integer timestamp");
    uint64_t value=0,limit=minus?(uint64_t(1)<<63):uint64_t(std::numeric_limits<Tick>::max());
    for(;p<s.size;++p){unsigned char c=s.data[p];if(c<'0'||c>'9'||value>(limit-(c-'0'))/10)throw std::runtime_error("invalid/overflow VCD integer timestamp");value=value*10+(c-'0');}
    if(minus&&value==(uint64_t(1)<<63))return std::numeric_limits<Tick>::min();
    return minus?-static_cast<Tick>(value):static_cast<Tick>(value);
}


#include <sstream>
#include <iomanip>
struct Val{uint32_t data,known;Val():data(0),known(0){}};
static Val number(const std::string&s,int w){Val v;std::string b=bits(s,w);if(b.size()>size_t(w))b=b.substr(b.size()-w);if(b.size()!=size_t(w)||w>32)throw std::runtime_error("invalid watched width");for(int i=0;i<w;++i){char c=b[b.size()-1-i];if(c=='0'||c=='1'){v.known|=uint32_t(1)<<i;if(c=='1')v.data|=uint32_t(1)<<i;}else if(c!='x'&&c!='z')throw std::runtime_error("invalid watched value");}return v;}
struct Mem{std::string name,kind;int bank,aw;size_t ck,ce,we,ad,wm,wd;std::vector<uint16_t>valid;long long reads,writes,bits_written;Mem():bank(0),aw(0),reads(0),writes(0),bits_written(0){}};
struct Gate{std::string name;size_t code;int width;uint32_t mask,value;};
struct Range{std::string name;size_t code;Tick start,end;uint32_t expected;};
struct Audit{
 Lookup lookup;std::unordered_map<std::string,size_t> ids;std::vector<std::string> now,next;std::vector<size_t> touched;std::vector<bool> dirty,isclock;std::vector<Range> ranges;std::vector<Mem> mems;std::vector<Gate> gates;bool initial;long long edges;
 Audit():initial(true),edges(0){}
 size_t id(const std::string&s){auto i=ids.find(s);if(i!=ids.end())return i->second;size_t n=now.size();ids[s]=n;lookup.add(s,n);now.push_back("x");next.push_back("");dirty.push_back(false);isclock.push_back(false);return n;}
 void config(const char*fn){std::ifstream f(fn);if(!f)throw std::runtime_error("config open failed");std::string s;while(std::getline(f,s)){if(s.empty())continue;std::vector<std::string>a;std::istringstream line(s);std::string v;while(std::getline(line,v,'\t'))a.push_back(v);if(a[0]=="M"){if(a.size()!=11)throw std::runtime_error("invalid memory spec");Mem m;m.name=a[1];m.kind=a[2];m.bank=std::stoi(a[3]);m.ck=id(a[4]);isclock[m.ck]=true;m.ce=id(a[5]);m.we=id(a[6]);m.ad=id(a[7]);m.wm=id(a[8]);m.wd=id(a[9]);m.aw=std::stoi(a[10]);m.valid.assign(size_t(1)<<m.aw,0);mems.push_back(m);}else if(a[0]=="V"){if(a.size()!=6)throw std::runtime_error("invalid gate spec");Gate g;g.name=a[1];g.code=id(a[2]);g.width=std::stoi(a[3]);g.mask=std::stoul(a[4],NULL,16);g.value=std::stoul(a[5],NULL,16);gates.push_back(g);}else if(a[0]=="R"){if(a.size()!=6)throw std::runtime_error("invalid range spec");Range r;r.name=a[1];r.code=id(a[2]);r.start=std::stoll(a[3]);r.end=std::stoll(a[4]);r.expected=std::stoul(a[5]);if(r.name.find("/clk")!=std::string::npos)isclock[r.code]=true;ranges.push_back(r);}else throw std::runtime_error("unknown config kind");}if(mems.empty())throw std::runtime_error("no memories configured");}
 uint32_t known(size_t i,int width){Val v=number(now[i],width);uint32_t mask=width==32?0xffffffffu:((uint32_t(1)<<width)-1);if((v.known&mask)!=mask)throw std::runtime_error("unknown active SRAM control/address");return v.data&mask;}
 void sample(Mem&m){if(known(m.ce,1))return;uint32_t addr=known(m.ad,m.aw);if(addr>=m.valid.size())throw std::runtime_error("macro address overflow");if(!known(m.we,1)){uint32_t enable=(~known(m.wm,16))&65535;Val d=number(now[m.wd],16);if((d.known&enable)!=enable)throw std::runtime_error("unknown enabled write data in "+m.name);m.valid[addr]|=enable;++m.writes;m.bits_written+=__builtin_popcount(enable);return;}uint32_t need=65535;if(m.kind=="X"){unsigned tile=addr>>5;if(tile>=20)throw std::runtime_error("unexpected X tile");int remaining=(tile==19?88:110)-16*m.bank;need=remaining<=0?0:remaining>=16?65535:(uint32_t(1)<<remaining)-1;}else if(m.kind=="ALPHA"&&addr>=99)throw std::runtime_error("unexpected alpha row");else if(m.kind=="W"&&addr>=64)throw std::runtime_error("unexpected weight address");if((m.valid[addr]&need)!=need){std::ostringstream e;e<<"read before current-task write "<<m.name<<" address="<<addr<<" missing="<<std::hex<<(need&~m.valid[addr]);throw std::runtime_error(e.str());}++m.reads;}
 void value(size_t i,const std::string&s){if(i==NONE)return;if(dirty[i]&&isclock[i]&&next[i]!=s)throw std::runtime_error("multiple clock transitions at one VCD tick");if(!dirty[i]){dirty[i]=true;touched.push_back(i);}next[i]=s;}
 void flush(Tick tm){if(!initial){for(auto&r:ranges)if(tm>=r.start&&tm<=r.end){Val a=number(now[r.code],1);Val b=number(dirty[r.code]?next[r.code]:now[r.code],1);if(a.known!=1||b.known!=1||a.data!=r.expected||b.data!=r.expected)throw std::runtime_error("CPU loading ownership state/clock changed "+r.name);}}if(!initial){for(auto&m:mems){Val a=number(now[m.ck],1);std::string v=dirty[m.ck]?next[m.ck]:now[m.ck];Val b=number(v,1);if(a.known!=1||b.known!=1)throw std::runtime_error("unknown macro clock");if(!a.data&&b.data){sample(m);++edges;}}}for(size_t i:touched){now[i]=next[i];dirty[i]=false;}touched.clear();if(initial){for(auto&g:gates){Val a=number(now[g.code],g.width);if((a.known&g.mask)!=g.mask||(a.data&g.mask)!=g.value)throw std::runtime_error("nonempty/unknown cold validity state "+g.name);}initial=false;}}
 void run(){Reader reader;Token t,c;bool header=false;while(reader.token(t)){if(equals(t,"$enddefinitions")){if(!reader.token(t)||!equals(t,"$end"))throw std::runtime_error("invalid header end");header=true;break;}}if(!header)throw std::runtime_error("no VCD header");Tick time=0;while(reader.token(t)){if(t.data[0]=='#'){Tick n=tick(t);if(n<time)throw std::runtime_error("VCD time reversed");if(n!=time){flush(time);time=n;}}else if(t.data[0]=='$'){if(equals(t,"$dumpoff"))throw std::runtime_error("dump disabled during task");if(equals(t,"$dumpvars")||equals(t,"$dumpall")||equals(t,"$dumpon")||equals(t,"$end"))continue;while(reader.token(t))if(equals(t,"$end"))break;}else if(t.data[0]=='b'||t.data[0]=='B'||t.data[0]=='r'||t.data[0]=='R'){std::string v(t.data,t.size);std::transform(v.begin(),v.end(),v.begin(),::tolower);if(!reader.token(c))throw std::runtime_error("vector missing ID");size_t i=lookup.find(c.data,c.size);if(i!=NONE)value(i,v);}else if(t.size>1){size_t i=lookup.find(t.data+1,t.size-1);if(i!=NONE){char v=std::tolower(t.data[0]);if(v!='0'&&v!='1'&&v!='x'&&v!='z')throw std::runtime_error("invalid scalar");value(i,std::string(1,v));}}else throw std::runtime_error("invalid VCD body");}flush(time);}
 void report(){long long r=0,w=0,b=0;for(auto&m:mems){r+=m.reads;w+=m.writes;b+=m.bits_written;}std::cout<<"{\"pass\":true,\"memories\":"<<mems.size()<<",\"cold_validity_signals\":"<<gates.size()<<",\"CPU_ownership_ranges\":"<<ranges.size()<<",\"macro_clock_edges\":"<<edges<<",\"read_operations\":"<<r<<",\"write_operations\":"<<w<<",\"enabled_written_bits\":"<<b<<",\"macros\":[";bool first=true;for(auto&m:mems){if(!first)std::cout<<",";first=false;std::cout<<"{\"kind\":\""<<m.kind<<"\",\"bank\":"<<m.bank<<",\"reads\":"<<m.reads<<",\"writes\":"<<m.writes<<"}";}std::cout<<"]}\n";}
};
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("usage: audit config.tsv < exact_cold.vcd");Audit a;a.config(argv[1]);a.run();a.report();return 0;}catch(const std::exception&e){std::cerr<<"AUDIT_FAIL "<<e.what()<<"\n";return 1;}}
