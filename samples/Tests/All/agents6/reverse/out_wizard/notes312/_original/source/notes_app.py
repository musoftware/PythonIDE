__doc__ = 'Small tkinter notes app used to test the exe importer.'
import json
import os
import tkinter as tk
from tkinter import messagebox
DATA = os.path.join(os.path.expanduser('~'), 'notes_test.json')
class Note:
    def __init__(self, title, body='', tags=None):
        self.title = title
        self.body = body
        self.tags = list(tags or [])
    
    def summary(self, width=20):
        # DECOMPILE-FAILED: summary (pop from empty list) - disassembly:
        #      2 LOAD_FAST            self
        #      4 LOAD_ATTR            body
        #     24 LOAD_ATTR            NULL|self + replace
        #     44 LOAD_CONST           '\n'
        #     46 LOAD_CONST           ' '
        #     48 CALL                 
        #     56 STORE_FAST           text
        #     58 LOAD_FAST            self
        #     60 LOAD_ATTR            title
        #     80 FORMAT_VALUE         
        #     82 LOAD_CONST           ': '
        #     84 LOAD_FAST            text
        #     86 LOAD_CONST           None
        #     88 LOAD_FAST            width
        #     90 BINARY_SLICE         
        #     92 FORMAT_VALUE         
        #     94 BUILD_STRING         
        #     96 LOAD_GLOBAL          NULL + len
        #    106 LOAD_FAST            text
        #    108 CALL                 
        #    116 LOAD_FAST            width
        #    118 COMPARE_OP           >
        #    122 POP_JUMP_IF_FALSE    to 132
        #    124 LOAD_CONST           '...'
        #    126 BINARY_OP            +
        #    130 RETURN_VALUE         
        #    132 LOAD_CONST           ''
        #    134 BINARY_OP            +
        #    138 RETURN_VALUE         
        raise NotImplementedError('summary could not be decompiled')
    
    def to_dict(self):
        return {'title': self.title, 'body': self.body, 'tags': self.tags}
    

def load_notes(path=DATA):
    # DECOMPILE-FAILED: load_notes (try/except/with) - disassembly:
    #      2 NOP                  
    #      4 LOAD_GLOBAL          NULL + open
    #     14 LOAD_FAST            path
    #     16 LOAD_CONST           'utf-8'
    #     18 KW_NAMES             ('encoding',)
    #     20 CALL                 
    #     28 BEFORE_WITH          
    #     30 STORE_FAST           f
    #     32 LOAD_GLOBAL          NULL + json
    #     42 LOAD_ATTR            load
    #     62 LOAD_FAST            f
    #     64 CALL                 
    #     72 GET_ITER             
    #     74 LOAD_FAST_AND_CLEAR  d
    #     76 SWAP                 
    #     78 BUILD_LIST           
    #     80 SWAP                 
    #     82 FOR_ITER             to 112
    #     86 STORE_FAST           d
    #     88 LOAD_GLOBAL          NULL + Note
    #     98 LOAD_CONST           ()
    #    100 BUILD_MAP            
    #    102 LOAD_FAST            d
    #    104 DICT_MERGE           
    #    106 CALL_FUNCTION_EX     
    #    108 LIST_APPEND          
    #    110 JUMP_BACKWARD        to 82
    #    112 END_FOR              
    #    114 SWAP                 
    #    116 STORE_FAST           d
    #    118 SWAP                 
    #    120 LOAD_CONST           None
    #    122 LOAD_CONST           None
    #    124 LOAD_CONST           None
    #    126 CALL                 
    #    134 POP_TOP              
    #    136 RETURN_VALUE         
    #    138 SWAP                 
    #    140 POP_TOP              
    #    142 SWAP                 
    #    144 STORE_FAST           d
    #    146 RERAISE              
    #    148 PUSH_EXC_INFO        
    #    150 WITH_EXCEPT_START    
    #    152 POP_JUMP_IF_TRUE     to 156
    #    154 RERAISE              
    #    156 POP_TOP              
    #    158 POP_EXCEPT           
    #    160 POP_TOP              
    #    162 POP_TOP              
    #    164 RETURN_CONST         None
    #    166 COPY                 
    #    168 POP_EXCEPT           
    #    170 RERAISE              
    #    172 PUSH_EXC_INFO        
    #    174 LOAD_GLOBAL          OSError
    #    184 LOAD_GLOBAL          ValueError
    #    194 BUILD_TUPLE          
    #    196 CHECK_EXC_MATCH      
    #    198 POP_JUMP_IF_FALSE    to 210
    #    200 POP_TOP              
    #    202 BUILD_LIST           
    #    204 SWAP                 
    #    206 POP_EXCEPT           
    #    208 RETURN_VALUE         
    #    210 RERAISE              
    #    212 COPY                 
    #    214 POP_EXCEPT           
    #    216 RERAISE              
    raise NotImplementedError('load_notes could not be decompiled')

def count_words(notes):
    total = 0
    for n in notes:
        for w in n.body.split():
            if w.isalpha():
                total += 1
                continue
            if w:
                continue
    return total

def tag_index(notes):
    # DECOMPILE-FAILED: tag_index (try/except/with) - disassembly:
    #      2 BUILD_MAP            
    #      4 STORE_FAST           idx
    #      6 LOAD_GLOBAL          NULL + enumerate
    #     16 LOAD_FAST            notes
    #     18 CALL                 
    #     26 GET_ITER             
    #     28 FOR_ITER             to 170
    #     32 UNPACK_SEQUENCE      
    #     36 STORE_FAST           i
    #     38 STORE_FAST           n
    #     40 LOAD_FAST            n
    #     42 LOAD_ATTR            tags
    #     62 GET_ITER             
    #     64 FOR_ITER             to 166
    #     68 STORE_FAST           t
    #     70 LOAD_FAST            idx
    #     72 LOAD_ATTR            NULL|self + setdefault
    #     92 LOAD_FAST            t
    #     94 LOAD_ATTR            NULL|self + lower
    #    114 CALL                 
    #    122 BUILD_LIST           
    #    124 CALL                 
    #    132 LOAD_ATTR            NULL|self + append
    #    152 LOAD_FAST            i
    #    154 CALL                 
    #    162 POP_TOP              
    #    164 JUMP_BACKWARD        to 64
    #    166 END_FOR              
    #    168 JUMP_BACKWARD        to 28
    #    170 END_FOR              
    #    172 LOAD_GLOBAL          NULL + sorted
    #    182 LOAD_FAST            idx
    #    184 LOAD_ATTR            NULL|self + items
    #    204 CALL                 
    #    212 CALL                 
    #    220 GET_ITER             
    #    222 LOAD_FAST_AND_CLEAR  k
    #    224 LOAD_FAST_AND_CLEAR  v
    #    226 SWAP                 
    #    228 BUILD_MAP            
    #    230 SWAP                 
    #    232 FOR_ITER             to 282
    #    236 UNPACK_SEQUENCE      
    #    240 STORE_FAST           k
    #    242 STORE_FAST           v
    #    244 LOAD_GLOBAL          NULL + len
    #    254 LOAD_FAST            v
    #    256 CALL                 
    #    264 LOAD_CONST           0
    #    266 COMPARE_OP           >
    #    270 POP_JUMP_IF_TRUE     to 274
    #    272 JUMP_BACKWARD        to 232
    #    274 LOAD_FAST            k
    #    276 LOAD_FAST            v
    #    278 MAP_ADD              
    #    280 JUMP_BACKWARD        to 232
    #    282 END_FOR              
    #    284 SWAP                 
    #    286 STORE_FAST           v
    #    288 STORE_FAST           k
    #    290 RETURN_VALUE         
    #    292 SWAP                 
    #    294 POP_TOP              
    #    296 SWAP                 
    #    298 STORE_FAST           v
    #    300 STORE_FAST           k
    #    302 RERAISE              
    raise NotImplementedError('tag_index could not be decompiled')

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Notes')
        self.notes = load_notes()
        self.entry = tk.Entry(self, width=40)
        self.entry.pack(padx=8, pady=4)
        tk.Button(self, text='Add', command=self.add).pack()
        self.listbox = tk.Listbox(self, width=50)
        self.listbox.pack(fill='both', expand=True)
        self.status = tk.Label(self, text='')
        self.status.pack()
        self.refresh()
    
    def add(self):
        # DECOMPILE-FAILED: add (try/except/with) - disassembly:
        #      2 LOAD_FAST            self
        #      4 LOAD_ATTR            entry
        #     24 LOAD_ATTR            NULL|self + get
        #     44 CALL                 
        #     52 LOAD_ATTR            NULL|self + strip
        #     72 CALL                 
        #     80 STORE_FAST           title
        #     82 LOAD_FAST            title
        #     84 POP_JUMP_IF_TRUE     to 132
        #     86 LOAD_GLOBAL          NULL + messagebox
        #     96 LOAD_ATTR            showwarning
        #    116 LOAD_CONST           'Notes'
        #    118 LOAD_CONST           'Type a title first'
        #    120 CALL                 
        #    128 POP_TOP              
        #    130 RETURN_CONST         None
        #    132 LOAD_FAST            self
        #    134 LOAD_ATTR            notes
        #    154 LOAD_ATTR            NULL|self + append
        #    174 LOAD_GLOBAL          NULL + Note
        #    184 LOAD_FAST            title
        #    186 LOAD_FAST            title
        #    188 LOAD_ATTR            NULL|self + split
        #    208 CALL                 
        #    216 GET_ITER             
        #    218 LOAD_FAST_AND_CLEAR  w
        #    220 SWAP                 
        #    222 BUILD_LIST           
        #    224 SWAP                 
        #    226 FOR_ITER             to 280
        #    230 STORE_FAST           w
        #    232 LOAD_FAST            w
        #    234 LOAD_ATTR            NULL|self + startswith
        #    254 LOAD_CONST           '#'
        #    256 CALL                 
        #    264 POP_JUMP_IF_TRUE     to 268
        #    266 JUMP_BACKWARD        to 226
        #    268 LOAD_FAST            w
        #    270 LOAD_CONST           1
        #    272 LOAD_CONST           None
        #    274 BINARY_SLICE         
        #    276 LIST_APPEND          
        #    278 JUMP_BACKWARD        to 226
        #    280 END_FOR              
        #    282 SWAP                 
        #    284 STORE_FAST           w
        #    286 KW_NAMES             ('tags',)
        #    288 CALL                 
        #    296 CALL                 
        #    304 POP_TOP              
        #    306 LOAD_FAST            self
        #    308 LOAD_ATTR            entry
        #    328 LOAD_ATTR            NULL|self + delete
        #    348 LOAD_CONST           0
        #    350 LOAD_CONST           'end'
        #    352 CALL                 
        #    360 POP_TOP              
        #    362 LOAD_FAST            self
        #    364 LOAD_ATTR            NULL|self + refresh
        #    384 CALL                 
        #    392 POP_TOP              
        #    394 RETURN_CONST         None
        #    396 SWAP                 
        #    398 POP_TOP              
        #    400 SWAP                 
        #    402 STORE_FAST           w
        #    404 RERAISE              
        raise NotImplementedError('add could not be decompiled')
    
    def refresh(self):
        self.listbox.delete(0, 'end')
        for n in self.notes:
            self.listbox.insert('end', n.summary())
        self.status.config(text=f"{len(self.notes)} notes, {count_words(self.notes)} words")
    

if __name__ == '__main__':
    App().mainloop()
