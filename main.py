import curses
import time

#
#   core stuff
#

class Keystroke:
    def __init__(self,key,timestamp):
        self.key=key
        self.time=timestamp

class Intent:
    def __init__(self,name,phrase, confidence, level, scope, reasons, preview):
        self.name=name #eg "delete"
        self.phrase=phrase #eg "dd"
        self.confidence=confidence
        self.level = level
        self.scope = scope
        self.reasons = reasons
        self.preview = preview

######################
#   intent engine    #
######################


class IntentEngine:
    def __init__(self):
        self.buffer=[] #recent keypressen
        self.window_ms=400 #phrase timing window of opportunity thing

        self.last_intent_phrase = None
        self.last_intent_time = None
        self.repeat_window_ms = 600
        self.repeat_level = 0

        #language/grammar
        self.phrases = {
            "dd": "delete",
            "cc": "clone",
            "wr": "wrap",
            "ii": "insert",
        }

    def feed(self,key):
        now=time.time()
        self.buffer.append(Keystroke(key,now))
        self._trim(now)

        phrase=self._current_phrase()

        if phrase in self.phrases:
            confidence = self._confidence_from_timing()
            level = self._resolve_repetition(phrase,now)
            scope = self._resolve_scope(confidence, level)
            reasons = self._explain(confidence, level)
            preview = self._resolve_preview(scope)

            return Intent(
                self.phrases[phrase],
                phrase,
                confidence,
                level,
                scope,
                reasons,
                preview
            )

    def _explain(self, confidence, level):
        reasons = []

        if confidence == "high":
            reasons.append("fast typing")
        elif confidence == "medium":
            reasons.append("moderate typing speed")
        else:
            reasons.append("slow or deliberate typing")

        if level > 1:
            reasons.append(f"repeated intent (x{level})")

        return reasons

    def _resolve_preview(self,scope):
        if scope == "character":
            return "current character"
        if scope == "word":
            return "current word"
        if scope == "line":
            return "current line"
        if scope == "block":
            return "current block"
        return "unknown"

    def _trim(self,now):
        self.buffer=[
            k for k in self.buffer
            if (now-k.time)*1000 <= self.window_ms
        ]

    def _current_phrase(self):
        chars =  []
        for k in self.buffer:
            if 32 <= k.key <= 126:
                chars.append(chr(k.key))
        return "".join(chars)

    def _average_interval_ms(self):
        if len(self.buffer) < 2:
            return None

        intervals = []
        for i in range(1, len(self.buffer)):
            dt = (self.buffer[i].time - self.buffer[i - 1].time) * 1000
            intervals.append(dt)

        return sum(intervals) / len(intervals)

    def _confidence_from_timing(self):
        avg = self._average_interval_ms()

        if avg is None:
            return "low"
        
        elif avg < 120:
            return "high"

        elif avg < 250:
            return "medium"

        else:
            return "low"

    def _resolve_repetition(self,phrase,now):
        if (
            self.last_intent_phrase == phrase
            and self.last_intent_time is not None
            and (now - self.last_intent_time) * 1000 <= self.repeat_window_ms
        ):
            self.repeat_level += 1
        else:
            self.repeat_level = 1

        self.last_intent_phrase = phrase
        self.last_intent_time = now

        return self.repeat_level

    def _resolve_scope(self, confidence, level):
        if level >= 3:
            return "block"

        if confidence == "high":
            return "line" if level >= 2 else "word"
        
        if confidence == "medium":
            return "word" if level == 1 else "line"

        return "character"

###########################################################################################################
######################################   ui  ##############################################################
###########################################################################################################

def draw_cursor(stdscr, y, x, char):
    try:
        stdscr.addstr(y, x, char, curses.A_REVERSE)
    except curses.error:
        pass

def delete_word(line, cursor_x):
    n = len(line)

    if cursor_x >= n:
        return line, cursor_x

    start = cursor_x

    while start < n and line[start].isspace():
        start += 1

    end = start

    while end < n and not line[end].isspace():
        end += 1

    if start == end:
        return line, cursor_x 

    new_line = line[:start] + line[end:]
    return new_line, start



def main(stdscr):
    curses.cbreak()
    curses.noecho()
    stdscr.keypad(True)
    curses.flushinp()
    pending_insert = False 
    curses.curs_set(1)

    engine = IntentEngine()

    status = "LISTENING"
    phrase_display = ""
    intent_display = "—"
    reason_display = ""
    preview_display = ""

    buffer = ["hello world"]
    cursor_x = 0
    cursor_y = 0



    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        #main
        stdscr.addstr(1,2,"Intent-Driven Editor")

        if max_y > 2:
            stdscr.addstr(0,0,buffer[cursor_y][:max_x-1])
            line = buffer[cursor_y]
            char = line[cursor_x] if cursor_x < len(line) else " "
            draw_cursor(stdscr, 0, cursor_x, char)

        #debug
        stdscr.addstr(3,2, f"PHRASE: {phrase_display}")
        stdscr.addstr(4,2, f"INTENT: {intent_display}")
        stdscr.addstr(5, 2, reason_display)
        stdscr.addstr(6, 2, preview_display)

        #status bar
        stdscr.addstr(
            max_y-1,
            0,
            status.ljust(max_x-1),
            curses.A_REVERSE
        )

        stdscr.refresh()

        key = stdscr.getch()

        if key == ord('q'):
            break

        if key == curses.KEY_LEFT:
            cursor_x = max(0, cursor_x - 1)
            continue
        elif key == curses.KEY_RIGHT:
            cursor_x = min(len(buffer[cursor_y]), cursor_x + 1)
            continue

        if pending_insert and 32 <= key <= 126:
            line = buffer[cursor_y]
            buffer[cursor_y] = line[:cursor_x] + chr(key) + line[cursor_x:]
            cursor_x += 1
            pending_insert = False
            continue

        intent = engine.feed(key)
        phrase_display =engine._current_phrase()

        if intent:
            intent_display = f"{intent.name} [{intent.confidence}] X{intent.level} → {intent.scope}"
            reason_display = "because: " + ", ".join(intent.reasons)
            preview_display = "preview: " + intent.preview
            status = "INTENT EMITTED"
        else:
            intent_display = "—"
            reason_display = ""
            preview_display = ""
            status = "LISTENING"

        if intent and intent.name == "insert":
            pending_insert = True

        if intent and intent.name == "delete" and intent.scope == "character":
            line = buffer[cursor_y]

            if cursor_x < len(line):
                buffer[cursor_y] = line[:cursor_x] + line[cursor_x+1:]
            elif cursor_x > 0:
                buffer[cursor_y] = line[:cursor_x-1] + line[cursor_x:]
                cursor_x -= 1

        if intent and intent.name == "delete" and intent.scope == "word":
            line = buffer[cursor_y]
            new_line, new_cursor_x = delete_word(line, cursor_x)
            buffer[cursor_y] = new_line
            cursor_x = new_cursor_x



if __name__ == "__main__":
    curses.wrapper(main)