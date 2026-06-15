import pytest
import time
from pathlib import Path
from aede.daemon.cron import CronStore, CronJob


def test_cron_store_init(tmp_home):
    store = CronStore(data_dir=tmp_home)
    assert store.data_dir == tmp_home
    assert store.db_path == tmp_home / "daemon_cron.db"


def test_cron_store_creates_db(tmp_home):
    store = CronStore(data_dir=tmp_home)
    assert store.db_path.exists()


def test_add_cron_job(tmp_home):
    store = CronStore(data_dir=tmp_home)
    job = store.add_job(schedule="0 9 * * *", action="daily_summary", label="daily")
    assert job.id is not None
    assert job.schedule == "0 9 * * *"
    assert job.action == "daily_summary"
    assert job.label == "daily"
    assert job.enabled is True


def test_add_cron_job_without_label(tmp_home):
    store = CronStore(data_dir=tmp_home)
    job = store.add_job(schedule="*/5 * * * *", action="ping")
    assert job.label == ""


def test_get_cron_job(tmp_home):
    store = CronStore(data_dir=tmp_home)
    added = store.add_job(schedule="0 * * * *", action="hourly")
    fetched = store.get_job(added.id)
    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.schedule == "0 * * * *"
    assert fetched.action == "hourly"


def test_get_cron_job_not_found(tmp_home):
    store = CronStore(data_dir=tmp_home)
    assert store.get_job("nonexistent") is None


def test_list_jobs(tmp_home):
    store = CronStore(data_dir=tmp_home)
    j1 = store.add_job(schedule="0 9 * * *", action="daily", label="daily")
    j2 = store.add_job(schedule="0 0 * * 0", action="weekly", label="weekly")
    jobs = store.list_jobs()
    assert len(jobs) == 2
    ids = {j.id for j in jobs}
    assert j1.id in ids
    assert j2.id in ids


def test_list_jobs_empty(tmp_home):
    store = CronStore(data_dir=tmp_home)
    assert store.list_jobs() == []


def test_delete_job(tmp_home):
    store = CronStore(data_dir=tmp_home)
    added = store.add_job(schedule="0 9 * * *", action="daily")
    assert store.get_job(added.id) is not None
    store.delete_job(added.id)
    assert store.get_job(added.id) is None


def test_delete_nonexistent_job(tmp_home):
    store = CronStore(data_dir=tmp_home)
    store.delete_job("nonexistent")


def test_enable_disable_job(tmp_home):
    store = CronStore(data_dir=tmp_home)
    added = store.add_job(schedule="0 9 * * *", action="daily")
    assert added.enabled is True
    store.set_enabled(added.id, False)
    fetched = store.get_job(added.id)
    assert fetched is not None
    assert fetched.enabled is False
    store.set_enabled(added.id, True)
    fetched = store.get_job(added.id)
    assert fetched is not None
    assert fetched.enabled is True


def test_get_enabled_jobs(tmp_home):
    store = CronStore(data_dir=tmp_home)
    j1 = store.add_job(schedule="0 9 * * *", action="daily")
    j2 = store.add_job(schedule="0 0 * * 0", action="weekly")
    store.set_enabled(j2.id, False)
    enabled = store.get_enabled_jobs()
    assert len(enabled) == 1
    assert enabled[0].id == j1.id


def test_persistence_across_restarts(tmp_home):
    store1 = CronStore(data_dir=tmp_home)
    added = store1.add_job(schedule="30 6 * * *", action="wake_up", label="persistent")
    store1.close()
    store2 = CronStore(data_dir=tmp_home)
    loaded = store2.get_job(added.id)
    assert loaded is not None
    assert loaded.schedule == "30 6 * * *"
    assert loaded.action == "wake_up"
    assert loaded.label == "persistent"
    assert loaded.enabled is True
    store2.close()


def test_last_run_at(tmp_home):
    store = CronStore(data_dir=tmp_home)
    added = store.add_job(schedule="0 9 * * *", action="daily")
    assert added.last_run_at is None
    now = int(time.time())
    store.set_last_run(added.id, now)
    fetched = store.get_job(added.id)
    assert fetched is not None
    assert fetched.last_run_at == now


def test_job_str(tmp_home):
    store = CronStore(data_dir=tmp_home)
    job = store.add_job(schedule="0 9 * * *", action="daily", label="daily report")
    s = str(job)
    assert "CronJob" in s
    assert job.id in s
    assert "daily report" in s
