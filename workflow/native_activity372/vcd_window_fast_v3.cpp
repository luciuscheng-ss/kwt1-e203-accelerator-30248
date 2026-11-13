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

struct Engine {
    std::vector<Signal> signals;
    std::unordered_map<std::string,size_t> ids;
    Lookup lookup;
    std::vector<std::pair<Tick,Tick> > gaps;
    std::vector<int> start_controls,end_controls;
    Tick start,end,raw_first,raw_last,previous;
    size_t header_bytes;
    bool rebase,started,finished,dumping;
    std::string initial_mode,block;
    std::ofstream output;
    std::vector<char> output_buffer;
    Engine(): start(0),end(0),raw_first(NA),raw_last(0),previous(0),header_bytes(0),
        rebase(false),started(false),finished(false),dumping(true),output_buffer(1024*1024) {}
    Tick out_tick(Tick t)const{return rebase?t-start:t;}
    void emit(std::string& dst,const Signal& s,const std::string& value) {
        dst+=value;
        if(!value.empty()&&(value[0]=='b'||value[0]=='r'))dst+=' ';
        dst+=s.code;dst+='\n';
    }
    void write(const std::string& text) {
        output.write(text.data(),static_cast<std::streamsize>(text.size()));
        if(!output)throw std::runtime_error("cropped VCD write failed");
    }
    void initialize() {
        started=true;
        block="#"+std::to_string(out_tick(start))+"\n$dumpvars\n";
        for(size_t i=0;i<signals.size();++i) {
            Signal& s=signals[i];
            if(s.present){emit(block,s,s.value);if(unknown(s.value))s.had_unknown=true;}
            if(s.tracked) {
                s.initial_present=s.last_present=s.present;
                s.initial=s.last=s.value;s.last_time=start;
                // Initial high snapshot is a level, not an observed rising edge.
            }
        }
        block+="$end\n";write(block);
    }
    void track(size_t index,const std::string& value,Tick time) {
        Signal& s=signals[index];
        bool different=!s.present||s.value!=value;
        if(different)s.changed=true;
        if(unknown(value))s.had_unknown=true;
        if(s.tracked) {
            if(!s.present||unknown(s.value))s.unknown_ticks+=time-s.last_time;
            if(different)++s.changes;
            std::string a=s.present?bits(s.value,s.width):std::string();
            std::string b=bits(value,s.width);
            if(s.present&&!a.empty()&&!b.empty()&&a.find_first_of("xz")==std::string::npos&&b.find_first_of("xz")==std::string::npos) {
                size_t count=std::min(a.size(),b.size());
                for(size_t n=0;n<count;++n)s.flips+=(a[n]!=b[n]);
            }
            if(s.width==1&&a=="0"&&b=="1") {
                if(s.last_rise!=NA) {
                    Tick p=time-s.last_rise;
                    s.min_period=s.min_period==NA?p:std::min(s.min_period,p);
                    s.max_period=s.max_period==NA?p:std::max(s.max_period,p);
                }
                ++s.rises;if(s.first_rise==NA)s.first_rise=time;s.last_rise=time;
            }
            s.last=value;s.last_present=true;s.last_time=time;
        }
        s.value=value;s.present=true;
    }
    void update_control(int control) {
        if(control==DUMPOFF)dumping=false;else if(control==DUMPON)dumping=true;
    }
    void process(Tick time,const std::vector<Event>& events,const std::string& arena) {
        if(raw_first==NA)raw_first=time;raw_last=time;
        if(!dumping&&previous<end&&time>start) {
            Tick a=std::max(previous,start),b=std::min(time,end);
            if(b>a)gaps.push_back(std::make_pair(a,b));
        }
        previous=time;
        if(time<start) {
            for(size_t i=0;i<events.size();++i) {
                const Event& e=events[i];
                if(e.control)update_control(e.control);
                else if(e.index!=NONE&&e.mode!=DUMPOFF){signals[e.index].value.assign(arena.data()+e.offset,e.length);signals[e.index].present=true;}
            }
            return;
        }
        if(!started) {
            bool any_current=false;
            for(size_t i=0;i<signals.size();++i)if(signals[i].present){any_current=true;break;}
            if(time==start) {
                for(size_t i=0;i<events.size();++i)if(events[i].control)start_controls.push_back(events[i].control);
                if(!dumping||!any_current) {
                    initial_mode="post_dumpon_snapshot_without_preedge_history";
                    for(size_t i=0;i<events.size();++i) {
                        const Event& e=events[i];
                        if(e.control)update_control(e.control);
                        else if(e.index!=NONE&&e.mode!=DUMPOFF){signals[e.index].value.assign(arena.data()+e.offset,e.length);signals[e.index].present=true;}
                    }
                    initialize();return;
                }
            }
            initial_mode="preedge_reconstructed_then_window_events";initialize();
        }
        if(time>=end) {
            if(time==end)for(size_t i=0;i<events.size();++i)if(events[i].control)end_controls.push_back(events[i].control);
            if(!finished){write("#"+std::to_string(out_tick(end))+"\n");finished=true;}
            return;
        }
        block.clear();
        for(size_t i=0;i<events.size();++i) {
            const Event& e=events[i];
            if(e.control)update_control(e.control);
            else if(e.index!=NONE&&e.mode!=DUMPOFF) {
                if(block.empty())block="#"+std::to_string(out_tick(time))+"\n";
                Signal& signal=signals[e.index];const char* value=arena.data()+e.offset;
                if(signal.tracked)track(e.index,std::string(value,e.length),time);
                else {
                    if(!signal.changed&&(!signal.present||signal.value.size()!=e.length||std::memcmp(signal.value.data(),value,e.length)!=0))signal.changed=true;
                    if(!signal.had_unknown&&e.length&&value[0]!='r')
                        for(size_t n=0;n<e.length;++n)if(value[n]=='x'||value[n]=='z'){signal.had_unknown=true;break;}
                    signal.present=true;
                }
                block.append(value,e.length);
                if(e.length&&(value[0]=='b'||value[0]=='r'))block+=' ';
                block+=signal.code;block+='\n';
            }
        }
        if(!block.empty())write(block);
    }
    void parse(Reader& reader) {
        Tick time=0;int mode=NO_CONTROL;
        std::vector<Event> events;events.reserve(4096);
        std::string arena;arena.reserve(1024*1024);Token word,code;
        while(reader.token(word)) {
            if(word.data[0]=='#') {
                Tick next=tick(word);
                if(next<time)throw std::runtime_error("VCD timestamp moves backwards");
                if(next!=time){if(!events.empty()||time!=0)process(time,events,arena);time=next;events.clear();arena.clear();}
            } else if(word.data[0]=='$') {
                int control=control_number(word);
                if(control){mode=control;events.push_back(Event(NONE,0,0,mode,NO_CONTROL));}
                else if(equals(word,"$end"))mode=NO_CONTROL;
                else {while(reader.token(word))if(equals(word,"$end"))break;}
            } else if(word.size>1&&(word.data[0]=='0'||word.data[0]=='1'||word.data[0]=='x'||word.data[0]=='X'||word.data[0]=='z'||word.data[0]=='Z')) {
                size_t index=lookup.find(word.data+1,word.size-1),offset=arena.size();
                char value=word.data[0];if(value>='A'&&value<='Z')value+=('a'-'A');arena+=value;
                events.push_back(Event(index,offset,1,NO_CONTROL,mode));
            } else if(word.data[0]=='b'||word.data[0]=='B'||word.data[0]=='r'||word.data[0]=='R') {
                size_t offset=arena.size(),length=word.size;arena.append(word.data,word.size);
                if(word.upper)for(size_t n=offset;n<arena.size();++n)if(arena[n]>='A'&&arena[n]<='Z')arena[n]+= ('a'-'A');
                if(!reader.token(code))throw std::runtime_error("VCD vector/real lacks identifier");
                events.push_back(Event(lookup.find(code.data,code.size),offset,length,NO_CONTROL,mode));
            } else throw std::runtime_error("unsupported/malformed VCD token: "+std::string(word.data,std::min(word.size,size_t(80))));
        }
        process(time,events,arena);
        if(!started||raw_last<end)throw std::runtime_error("VCD ends before requested task interval");
        if(!finished)write("#"+std::to_string(out_tick(end))+"\n");
        for(size_t i=0;i<signals.size();++i) {
            Signal& s=signals[i];
            if(s.tracked&&(!s.last_present||unknown(s.last)))s.unknown_ticks+=end-s.last_time;
        }
        output.close();if(!output)throw std::runtime_error("cropped VCD close failed");
    }
    void report(const std::string& path) {
        std::ofstream out(path.c_str());
        if(!out)throw std::runtime_error("cannot create statistics");
        out<<"META\t"<<raw_first<<'\t'<<raw_last<<'\t'<<initial_mode<<'\n';
        for(size_t i=0;i<start_controls.size();++i)out<<"START_CONTROL\t"<<control_name(start_controls[i])<<'\n';
        for(size_t i=0;i<end_controls.size();++i)out<<"END_CONTROL\t"<<control_name(end_controls[i])<<'\n';
        for(size_t i=0;i<gaps.size();++i)out<<"GAP\t"<<gaps[i].first<<'\t'<<gaps[i].second<<'\n';
        for(size_t i=0;i<signals.size();++i) {
            const Signal& s=signals[i];
            out<<"ID\t"<<s.code<<'\t'<<s.present<<'\t'<<s.changed<<'\t'<<s.had_unknown<<'\t'<<s.tracked;
            if(s.tracked)out<<'\t'<<(s.initial_present?s.initial:"-")<<'\t'<<(s.last_present?s.last:"-")
                <<'\t'<<s.last_time<<'\t'<<s.changes<<'\t'<<s.flips<<'\t'<<s.unknown_ticks<<'\t'<<s.rises
                <<'\t'<<s.first_rise<<'\t'<<s.last_rise<<'\t'<<s.min_period<<'\t'<<s.max_period;
            out<<'\n';
        }
        out<<"COMPLETE\t1\n";out.close();if(!out)throw std::runtime_error("statistics write failed");
    }
};

int main(int argc,char** argv) {
    try {
        if(argc!=4)throw std::runtime_error("usage: engine CONFIG CROP_VCD STATS_TSV < RAW_VCD");
        Engine e;std::ifstream cfg(argv[1]);int rebased;
        if(!(cfg>>e.header_bytes>>e.start>>e.end>>rebased)||e.start<0||e.end<=e.start)
            throw std::runtime_error("invalid engine configuration");
        e.rebase=rebased!=0;std::string code;size_t width;int tracked;
        while(cfg>>code>>width>>tracked) {
            if(!width||e.ids.count(code))throw std::runtime_error("invalid/duplicate VCD identifier configuration");
            Signal s;s.code=code;s.width=width;s.tracked=tracked!=0;e.signals.push_back(s);
        }
        if(!cfg.eof())throw std::runtime_error("invalid identifier configuration row");
        std::sort(e.signals.begin(),e.signals.end(),[](const Signal&a,const Signal&b){return a.code<b.code;});
        for(size_t i=0;i<e.signals.size();++i){e.ids[e.signals[i].code]=i;e.lookup.add(e.signals[i].code,i);}
        e.output.rdbuf()->pubsetbuf(&e.output_buffer[0],e.output_buffer.size());
        e.output.open(argv[2],std::ios::binary);
        if(!e.output)throw std::runtime_error("cannot create cropped VCD");
        Reader reader;std::string header;header.reserve(std::min(e.header_bytes,size_t(1024*1024)));
        for(size_t i=0;i<e.header_bytes;++i) {
            int ch=reader.get();if(ch==EOF)throw std::runtime_error("input shorter than verified header");
            if(ch>127)throw std::runtime_error("non-ASCII VCD header");header.push_back(static_cast<char>(ch));
            if(header.size()>=1024*1024){e.write(header);header.clear();}
        }
        if(!header.empty())e.write(header);
        e.parse(reader);e.report(argv[3]);
        std::cout<<"VCD_FAST_COMPLETE\n";return 0;
    } catch(const std::exception& error) {
        std::cerr<<"VCD_FAST_ERROR: "<<error.what()<<'\n';return 2;
    }
}
