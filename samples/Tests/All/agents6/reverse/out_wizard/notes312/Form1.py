from Form1_designer import Form1Designer, EventArgs  # noqa: F401
import json
import os
from tkinter import messagebox


DATA = os.path.join(os.path.expanduser('~'), 'notes_test.json')


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


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        pass


if __name__ == "__main__":
    Form1().show()
