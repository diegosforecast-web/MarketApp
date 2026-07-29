alter table public.profiles
    add column if not exists cancel_at_period_end boolean not null default false,
    add column if not exists canceled_at timestamptz,
    add column if not exists trial_end timestamptz;