''' Plugin for CudaText editor
Authors:
    Andrey Kvichansky    (kvichans on github.com)
Version:
    '0.8.2 2017-07-12'
ToDo: (see end of file)
'''

import  re, os, sys, glob, json, collections
from    fnmatch         import fnmatch
import  cudatext            as app
from    cudatext        import ed
import  cudatext_cmd        as cmds
import  cudax_lib           as apx
from    .cd_plug_lib    import *

#OrdDict = collections.OrderedDict
FROM_API_VERSION= '1.0.187'     # LEXER_GET_PROP

pass;                           LOG = (-2==-2)  # Do or dont logging.
pass;                           from pprint import pformat
pass;                           pf=lambda d:pformat(d,width=150)

_   = get_translation(__file__) # I18N

NO_LXR_SIGN = _('(none)')
class Command:
    def __init__(self):#NOTE: init
        if app.app_api_version()<FROM_API_VERSION:  return app.msg_status(_('Need update application'))
        self.wrap       = apx.get_opt('intextbookmk_wrap'            , apx.get_opt('ibm_wrap'            , True))
        self.show_wo_alt= apx.get_opt('intextbookmk_compact_show'    , apx.get_opt('ibm_compact_show'    , True))
#       self.show_wo_alt= apx.get_opt('intextbookmk_compact_show'    , apx.get_opt('ibm_compact_show'    , False))
        self.unlxr_cmnt = apx.get_opt('intextbookmk_no_lexer_comment', apx.get_opt('ibm_no_lexer_comment', '//'))
        self.bm_signs   = apx.get_opt('intextbookmk_signs'           , apx.get_opt('ibm_signs'           , ['NOTE:', 'NB!', 'TODO:', 'todo:', 'todo.', 'FIX:']))
        self.bm_signs   = [self.bm_signs] if type(self.bm_signs)==str else self.bm_signs
        self.bm_sign    = self.bm_signs[0]
        self.lxr2cmnt   = {NO_LXR_SIGN:self.unlxr_cmnt}
        self.ext2lxr    = {}
        for lxr in apx.get_enabled_lexers():
            cmnt                    = app.lexer_proc(app.LEXER_GET_PROP, lxr)['c_line']
#           cmnt                    = app.lexer_proc(app.LEXER_GET_COMMENT, lxr)
            if not cmnt:
                continue#for lxr
            self.lxr2cmnt[lxr]      = cmnt
            for ext in app.lexer_proc(app.LEXER_GET_PROP, lxr)['typ']:
                self.ext2lxr[ext]   = lxr
#           for ext in app.lexer_proc(app.LEXER_GET_EXT, lxr).split():
#               self.ext2lxr[ext]   = lxr
           #for lxr
       #def __init__

    def add_ibm(self):
        lxr         = ed.get_prop(app.PROP_LEXER_FILE)
        lxr         = lxr if lxr else NO_LXR_SIGN
#       if lxr not in self.lxr2cmnt:    return app.msg_status(f(_('Cannot add in-text bookmark into document with Lexer {}. No to-end-of-line comment.'), lxr))
        if lxr not in self.lxr2cmnt:    return app.msg_status(f(_('Cannot add in-text bookmark: no line-comments defined for lexer {}.'), lxr))
        cmnt        = self.lxr2cmnt[lxr]
        bm_msg      = app.dlg_input(_('Enter message for in-text bookmark. Empty is good.'), '')
        if bm_msg is None:              return
        (cCrt, rCrt
        ,cEnd, rEnd)= ed.get_carets()[0]
        line_s      = ed.get_text_line( rCrt)
        ed.set_text_line(               rCrt, line_s + cmnt + self.bm_sign + ' ' + bm_msg)
       #def add_ibm

    def next_ibm(self):
        self._jump_to_ibm('next')
    def prev_ibm(self):
        self._jump_to_ibm('prev')
    def _jump_to_ibm(self, what):
        ibms,   \
        msg     = self._ibms_in_tab(ed, self.bm_signs)
        if not ibms and msg:    return app.msg_status(msg)
        if not ibms:            return app.msg_status(_('No in-text bookmarks'))
        rCrt    = ed.get_carets()[0][1]
        if  1==len(ibms) \
        and rCrt==ibms[0][1]:   return app.msg_status(_('No more bookmarks'))
        line_ns = [line_n for (tab_id, line_n, bm_msg, line_s, tab_info) in ibms]
        if self.wrap:
            line_ns = [-line_ns[-1]] + line_ns + [line_ns[0]+0xFFFFFFFF]
        line_cns= [line_n for line_n in line_ns 
                    if (line_n>rCrt if what=='next' else line_n<rCrt)]
        if not line_cns:        return app.msg_status(_('No bookmark for jump'))
        line_n  = min(line_cns)         if what=='next'         else max(line_cns)
        line_n  = -line_n               if line_n<0             else line_n
        line_n  =  line_n-0xFFFFFFFF    if line_n>=0xFFFFFFFF   else line_n
        ed.set_caret(0, line_n)
        if not (ed.get_prop(app.PROP_LINE_TOP) <= line_n <= ed.get_prop(app.PROP_LINE_BOTTOM)):
            ed.set_prop(app.PROP_LINE_TOP, str(max(0, line_n - max(5, apx.get_opt('find_indent_vert')))))

    def _ibms_in_tab(self, ted, bm_signs):
        """ Collect in-text bm in the ted.
            Params
                ted         tab
                bm_signs    list of parsed signs
            Return
                list        [(tab_id, line_n, bm_msg, line_s, tab_info)]
                msg         Reason of empty list
        """
        lxr     = ted.get_prop(app.PROP_LEXER_FILE)
        lxr     = lxr if lxr else NO_LXR_SIGN
        if lxr not in self.lxr2cmnt:    return [], app.msg_status(f(_('No in-text bookmark into document with Lexer {}'), lxr))
        cmnt    =     self.lxr2cmnt[lxr]

        tab_sps = ' '*ted.get_prop(app.PROP_TAB_SIZE)
        tab_grp = ted.get_prop(app.PROP_INDEX_GROUP)
        tab_num = ted.get_prop(app.PROP_INDEX_TAB)
        tab_cap = ted.get_prop(app.PROP_TAB_TITLE)
        tab_id  = ted.get_prop(app.PROP_TAB_ID)
        tab_info= f('{}:{}. {}', 1+tab_grp, 1+tab_num, tab_cap)
        signs   = [cmnt + sign + ' ' for sign in bm_signs]
        pass;                  #LOG and log('signs={}',(signs))
        ibms    = []
        for line_n in range(ted.get_line_count()):
            line_s  = ted.get_text_line(line_n)
            for sign in signs:
                if sign in line_s:
                    line_s  = line_s.replace('\t', tab_sps)
                    bm_msg  = line_s[line_s.index(sign)+len(sign):]
                    ibms   += [(tab_id, line_n, bm_msg, line_s, tab_info)]
                    break#for sign
               #for sign
           #for line_n
        return ibms, ''
       #def _ibms_in_tab

    def dlg_ibms_in_tab(self):
        ibms,   \
        msg     = self._ibms_in_tab(ed, self.bm_signs)
        if not ibms and msg:    return app.msg_status(msg)
        if not ibms:            return app.msg_status(_('No in-text bookmarks'))
        line_max= max([line_n for (tab_id, line_n, bm_msg, line_s, tab_info) in ibms])
        ln_wd   = len(str(line_max))
        pass;                  #LOG and log('ln_wd={}',(ln_wd))
        ibms    = [(bm_msg, line_n, f('{} {}', str(1+line_n).rjust(ln_wd, ' '), line_s)) 
                for (tab_id, line_n, bm_msg, line_s, tab_info) in ibms]
        pass;                  #LOG and log('ibms=¶{}',pf(ibms))
        rCrt    = ed.get_carets()[0][1]
        near    = min([(abs(line_n-rCrt), ind) 
                for ind, (bm_msg, line_n, line_s) in enumerate(ibms)])[1]
        if self.show_wo_alt:
            ans = app.dlg_menu(app.MENU_LIST, '\n'.join(
                    [f('{}\t{}', line_nd, bm_msg) for bm_msg, line_n, line_nd in ibms]
                ), near)
        else:
            ans = app.dlg_menu(app.MENU_LIST_ALT, '\n'.join(
                    [f('{}\t{}', bm_msg, line_nd) for bm_msg, line_n, line_nd in ibms]
                ), near)
        if ans is None:     return
        bm_msg, line_n, line_nd    = ibms[ans]
        ed.set_caret(0, line_n)
        if not (ed.get_prop(app.PROP_LINE_TOP) <= line_n <= ed.get_prop(app.PROP_LINE_BOTTOM)):
            ed.set_prop(app.PROP_LINE_TOP, str(max(0, line_n - max(5, apx.get_opt('find_indent_vert')))))
       #def dlg_ibms_in_tab

    def dlg_ibms_in_tabs(self):
        ibms    = []
        for h_tab in app.ed_handles(): 
            ted     = app.Editor(h_tab)
            t_ibms, \
            msg     = self._ibms_in_tab(ted, self.bm_signs)
            ibms   += t_ibms
           #for h_tab
        if not ibms:    return app.msg_status(_('No in-text bookmarks in tabs'))
        line_max= max([line_n for (tab_id, line_n, bm_msg, line_s, tab_info) in ibms])
        ln_wd   = len(str(line_max))
        ibms    = [(tab_id, line_n, bm_msg, f('{} {}', str(1+line_n).rjust(ln_wd, ' '), line_s), tab_info) 
                    for (tab_id, line_n, bm_msg, line_s, tab_info) in ibms]
        tid     = ed.get_prop(app.PROP_TAB_ID)
        rCrt    = ed.get_carets()[0][1]
        near    = min([(abs(line_n-rCrt) if tid==tab_id else 0xFFFFFF, ind) 
                    for ind, (tab_id, line_n, bm_msg, line_s, tab_info) in enumerate(ibms)])[1]
        ans     = app.dlg_menu(app.MENU_LIST_ALT, '\n'.join(
                    [f('({}) {}\t{}', tab_info, bm_msg, line_s) for tab_id, line_n, bm_msg, line_s, tab_info in ibms]
                ), near)
        if ans is None: return
        tab_id, line_n, bm_msg, line_s, tab_info    = ibms[ans]
        ted     = apx.get_tab_by_id(tab_id)
        ted.focus()
        ed.set_caret(0, line_n)
        if not (ed.get_prop(app.PROP_LINE_TOP) <= line_n <= ed.get_prop(app.PROP_LINE_BOTTOM)):
            ed.set_prop(app.PROP_LINE_TOP, str(max(0, line_n - max(5, apx.get_opt('find_indent_vert')))))
       #def dlg_ibms_in_tabs

    def dlg_config(self):
        DLG_W,  \
        DLG_H   = 400, 95
        lxrs_l  = apx.get_enabled_lexers()
        
        sgns_h  = _('Space delimeted list.\rThe first word will be inserted by command.')
        dfcm_h  = _('Default comment sign.\rIt is used when lexer has no line comment or file has no lexer.')
        cnts    =[dict(           tp='lb'   ,tid='sgns' ,l=GAP          ,w=130          ,cap=_('&Bookmark signs:')  ,hint=sgns_h    ) # &b
                 ,dict(cid='sgns',tp='ed'   ,t=GAP      ,l=130          ,w=DLG_W-130-GAP                                            ) #  
                 ,dict(           tp='lb'   ,tid='dfcm' ,l=GAP          ,w=130          ,cap=_('&Comment sign:')    ,hint=dfcm_h    ) # &c 
                 ,dict(cid='dfcm',tp='ed'   ,t=35       ,l=130          ,w=DLG_W-130-GAP                                            ) #  
                 ,dict(cid='wrap',tp='ch'   ,tid='!'    ,l=GAP          ,w=120          ,cap=_('&Wrap for next/prev')               ) # &w
#                ,dict(cid='help',tp='bt'   ,t=DLG_H-60 ,l=DLG_W-GAP-80 ,w=80           ,cap=_('Help')                              ) #  
                 ,dict(cid='!'   ,tp='bt'   ,t=DLG_H-30 ,l=DLG_W-GAP-165,w=80           ,cap=_('Save')          ,props='1'          ) #     default
                 ,dict(cid='-'   ,tp='bt'   ,t=DLG_H-30 ,l=DLG_W-GAP-80 ,w=80           ,cap=_('Close')                             ) #  
                ]#NOTE: cfg
        focused = 'sgns'
        while True:
            act_cid, vals, chds = dlg_wrapper(_('In-text bookmarks'), DLG_W, DLG_H, cnts
                , dict(sgns=' '.join(self.bm_signs)
                      ,dfcm=         self.unlxr_cmnt
                      ,wrap=         self.wrap
                      ), focus_cid=focused)
            if act_cid is None or act_cid=='-':    return#while True
            focused = chds[0] if 1==len(chds) else focused
            if act_cid=='!':
                if not vals['sgns'].strip():
                    app.msg_status(_('Need Bookmark sign'))
                    focused = 'sgns'
                    continue#while
                if not vals['dfcm'].strip():
                    app.msg_status(_('Need Comment sign'))
                    focused = 'dfcm'
                    continue#while
                if  self.bm_signs  != vals['sgns'].split():
                    self.bm_signs   = vals['sgns'].split()
                    apx.set_opt('intextbookmk_signs', self.bm_signs)
                if  self.unlxr_cmnt!= vals['dfcm'].strip():
                    self.unlxr_cmnt = vals['dfcm'].strip()
                    apx.set_opt('intextbookmk_no_lexer_comment', self.unlxr_cmnt)
                if  self.wrap      != vals['wrap']:
                    self.wrap       = vals['wrap']
                    apx.set_opt('intextbookmk_wrap', self.wrap)
                break#while
           #while
       #def dlg_config

#   def dlg_ibms_in_dir(self):
#       return app.msg_status(f(_('No release yet')))
#      #def dlg_ibms_in_dir
   #class Command

'''
ToDo
[+][kv-kv][11may16] Start
[?][kv-kv][11may16] Replace msg in current line?
[?][kv-kv][11may16] Two methods or one opt ibm_compact_show?
'''
