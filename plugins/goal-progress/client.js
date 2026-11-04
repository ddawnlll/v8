window.__ModuleLoader__.load({
  id: '@local/goal-progress',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const NS = 'goal-progress';

    const en = {
      label: 'Goal progress',
      labelComplete: 'Goal complete',
      tasks: 'tasks done',
      round: 'round',
      now: 'Now',
      next: 'Next',
      allDone: 'All tasks done',
      waiting: 'Waiting for the agent to write a task list',
      expand: 'Show task list',
      collapse: 'Hide task list',
      basisTasks: 'Percent of tasks completed in the current plan',
      basisRounds: 'No task list yet — the agent has not planned this goal',
      basisComplete: 'The goal is marked complete',
      phasePaused: 'paused',
      phaseBlocked: 'blocked',
    };

    const zh = {
      label: '目标进度',
      labelComplete: '目标已完成',
      tasks: '任务已完成',
      round: '轮次',
      now: '当前',
      next: '下一步',
      allDone: '全部任务已完成',
      waiting: '等待代理写入任务清单',
      expand: '展开任务清单',
      collapse: '收起任务清单',
      basisTasks: '当前计划中已完成任务所占百分比',
      basisRounds: '暂无任务清单 — 代理尚未规划该目标',
      basisComplete: '目标已完成',
      phasePaused: '已暂停',
      phaseBlocked: '受阻',
    };

    const CSS = [
      '.gp_dock{box-sizing:border-box;width:calc(100% - var(--dsh-composer-side-clearance) - var(--dsh-composer-side-clearance) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset));margin:0 auto;animation:gp_enter .28s ease-out}',
      '.gp_bar{isolation:isolate;box-sizing:border-box;width:100%;max-width:calc(var(--dsh-composer-card-max-width) - 4 * var(--dsh-composer-dock-inset));border-radius:var(--dsw-radius-md);background:var(--dsw-specific-menu);backdrop-filter:var(--dsw-menu-backdrop-filter);box-shadow:var(--dsw-elevation-panel);margin:0 auto;padding:7px 10px 7px 12px;display:flex;flex-direction:column;gap:4px;position:relative}',
      '.gp_top{display:flex;align-items:center;gap:10px;width:100%;min-width:0}',
      '.gp_label{flex:none;color:var(--dsw-alias-label-primary);font-size:13px;font-weight:500;line-height:20px;white-space:nowrap}',
      '.gp_track{flex:1;min-width:48px;height:6px;border-radius:999px;background:var(--dsw-alias-bg-layer-2);overflow:hidden}',
      '.gp_fill{position:relative;height:100%;border-radius:999px;background:var(--dsw-alias-brand-primary);overflow:hidden;transition:width .45s cubic-bezier(.22,.61,.36,1),background-color .3s ease}',
      '.gp_fill::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,.38) 50%,transparent 100%);transform:translateX(-120%);opacity:0}',
      '.gp_fill[data-animated="true"]::after{opacity:1;animation:gp_sheen 1.8s linear infinite}',
      '.gp_fill[data-indeterminate="true"]{width:35% !important;opacity:.45}',
      '.gp_fill[data-phase="active"][data-indeterminate="true"]{opacity:1;animation:gp_indet 1.5s ease-in-out infinite}',
      '@keyframes gp_indet{0%{transform:translateX(-120%)}100%{transform:translateX(300%)}}',
      '@keyframes gp_enter{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}',
      '@keyframes gp_sheen{from{transform:translateX(-120%)}to{transform:translateX(120%)}}',
      '.gp_fill[data-phase="paused"]{background:var(--dsw-alias-state-idle-primary)}',
      '.gp_fill[data-phase="blocked"]{background:var(--dsw-alias-state-error-primary)}',
      '.gp_fill[data-complete="true"]{background:var(--dsw-alias-state-success-primary)}',
      '.gp_percent{flex:none;min-width:38px;text-align:right;color:var(--dsw-alias-label-primary);font-size:13px;font-weight:600;line-height:20px;font-variant-numeric:tabular-nums;transition:color .3s ease}',
      '.gp_toggle{flex:none;width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:6px;background:transparent;color:var(--dsw-alias-label-secondary);font-size:11px;line-height:1;cursor:pointer;padding:0}',
      '.gp_toggle:hover{background:var(--dsw-alias-bg-layer-2);color:var(--dsw-alias-label-primary)}',
      '.gp_toggle:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:1px}',
      '.gp_now{display:flex;align-items:center;gap:6px;min-width:0;color:var(--dsw-alias-label-secondary);font-size:12px;line-height:18px}',
      '.gp_nowIcon{flex:none;color:var(--dsw-alias-brand-primary);font-size:11px}',
      '.gp_nowText{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.gp_list{list-style:none;margin:2px 0 0;padding:6px 0 0;border-top:1px solid var(--dsw-alias-border-l1);display:flex;flex-direction:column;gap:3px;max-height:200px;overflow:auto}',
      '.gp_item{display:flex;align-items:flex-start;gap:7px;font-size:12px;line-height:17px;color:var(--dsw-alias-label-secondary)}',
      '.gp_itemIcon{flex:none;width:13px;text-align:center;font-size:11px;line-height:17px}',
      '.gp_item[data-status="in_progress"]{color:var(--dsw-alias-label-primary);font-weight:500}',
      '.gp_item[data-status="in_progress"] .gp_itemIcon{color:var(--dsw-alias-brand-primary)}',
      '.gp_item[data-status="completed"]{color:var(--dsw-alias-label-secondary);opacity:.75}',
      '.gp_item[data-status="completed"] .gp_itemIcon{color:var(--dsw-alias-state-success-primary)}',
      '.gp_itemText{min-width:0;overflow-wrap:anywhere}',
      '@media (max-width:520px){.gp_label{display:none}}',
      '@media (prefers-reduced-motion:reduce){.gp_dock{animation:none}.gp_fill{transition:none}.gp_fill::after{animation:none;display:none}.gp_fill[data-indeterminate="true"]{animation:none}}',
    ].join('');

    const PHASE_LABEL = { paused: 'phasePaused', blocked: 'phaseBlocked' };
    const STATUS_ICON = { completed: '✓', in_progress: '▶', pending: '○' };

    function clamp(value) {
      if (!Number.isFinite(value)) return 0;
      return Math.max(0, Math.min(100, value));
    }

    function GoalProgress(props) {
      const [open, setOpen] = React.useState(false);
      const useProjection = props.useProjection;
      const translate = typeof props.t === 'function' ? props.t : (key) => en[key] || key;
      const projection = useProjection('goal');
      const todos = useProjection('todos');

      const goal = projection === undefined || projection === null ? undefined : projection.goal;
      if (goal === undefined || goal === null) return null;

      const complete = goal.phase === 'complete';
      const list = Array.isArray(todos) ? todos : [];
      const total = list.length;
      const done = total === 0 ? 0 : list.filter((item) => item && item.status === 'completed').length;
      const roundsStarted = typeof projection.roundsStarted === 'number' ? projection.roundsStarted : 0;
      const cap = typeof goal.maxGoalRounds === 'number' ? goal.maxGoalRounds : 0;

      const taskRatio = total > 0 ? (done / total) * 100 : null;
      const percent = complete
        ? 100
        : taskRatio !== null ? Math.round(clamp(taskRatio)) : null;
      const byTasks = !complete && taskRatio !== null;
      const basis = complete
        ? translate('basisComplete')
        : byTasks ? translate('basisTasks') : translate('basisRounds');
      const title = complete ? translate('labelComplete') : translate('label');

      const roundText = cap > 0 ? translate('round') + ' ' + roundsStarted + '/' + cap : '';
      const active = list.find((item) => item && item.status === 'in_progress');
      const pending = list.find((item) => item && item.status === 'pending');
      const phaseText = PHASE_LABEL[goal.phase] !== undefined ? translate(PHASE_LABEL[goal.phase]) : '';

      let nowIcon = '▶';
      let nowText = '';
      if (complete) {
        nowText = roundText;
      } else if (total === 0) {
        nowText = translate('waiting') + (roundText === '' ? '' : ' · ' + roundText);
      } else if (active !== undefined) {
        nowText = done + '/' + total + ' · ' + active.content;
      } else if (pending !== undefined) {
        nowIcon = '○';
        nowText = translate('next') + ': ' + pending.content + ' · ' + done + '/' + total;
      } else {
        nowIcon = '✓';
        nowText = translate('allDone') + (roundText === '' ? '' : ' · ' + roundText);
      }
      if (phaseText !== '') nowText = nowText + ' · ' + phaseText;

      const fillProps = {
        className: 'gp_fill',
        'data-phase': goal.phase,
        'data-complete': percent === 100 ? 'true' : 'false',
        'data-animated': goal.phase === 'active' && percent !== null && percent < 100 ? 'true' : 'false',
        'data-indeterminate': percent === null ? 'true' : 'false',
        style: { width: percent === null ? '35%' : percent + '%' },
      };

      const barProps = {
        className: 'gp_track',
        role: 'progressbar',
        'aria-label': title + (percent === null ? ' — ' + basis : ': ' + percent + '% — ' + basis),
      };
      if (percent !== null) {
        barProps['aria-valuemin'] = 0;
        barProps['aria-valuemax'] = 100;
        barProps['aria-valuenow'] = percent;
      }

      const items = open && total > 0
        ? h(
          'ul',
          { className: 'gp_list' },
          list.map((item, index) =>
            h(
              'li',
              { key: index, className: 'gp_item', 'data-status': item.status },
              h('span', { className: 'gp_itemIcon', 'aria-hidden': true }, STATUS_ICON[item.status] || '○'),
              h('span', { className: 'gp_itemText' }, item.content),
            ),
          ),
        )
        : null;

      return h(
        React.Fragment,
        null,
        h('style', { key: 'style', dangerouslySetInnerHTML: { __html: CSS } }),
        h(
          'div',
          { className: 'gp_dock', 'data-goal-progress': true },
          h(
            'div',
            { className: 'gp_bar', title: basis },
            h(
              'div',
              { className: 'gp_top' },
              h('span', { className: 'gp_label' }, title),
              h(
                'span',
                barProps,
                h('span', fillProps),
              ),
              h('span', { className: 'gp_percent' }, percent === null ? '—' : percent + '%'),
              total > 0 && !complete
                ? h(
                  'button',
                  {
                    type: 'button',
                    className: 'gp_toggle',
                    onClick: () => setOpen(!open),
                    'aria-expanded': open,
                    'aria-label': open ? translate('collapse') : translate('expand'),
                    title: open ? translate('collapse') : translate('expand'),
                  },
                  open ? '▴' : '▾',
                )
                : null,
            ),
            nowText === ''
              ? null
              : h(
                'div',
                { className: 'gp_now' },
                h('span', { className: 'gp_nowIcon', 'aria-hidden': true }, nowIcon),
                h('span', { className: 'gp_nowText', title: nowText }, nowText),
              ),
            items,
          ),
        ),
      );
    }

    return {
      inject: ['slots', 'locale'],
      apply(ctx) {
        ctx.effect(
          () => ctx.locale.register(NS, { zh, en }),
          'goal-progress: dictionaries',
        );
        ctx.slots.inject('conversation.input.dock', () =>
          ctx.slots.register(
            {
              name: 'conversation.input.dock',
              id: 'goal-progress',
              order: 11,
              locale: NS,
            },
            GoalProgress,
          ),
        );
      },
    };
  },
});
