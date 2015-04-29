#! /usr/bin/python
import re
import signal
import sys
import time
from threading import Event, Thread
from jenkinsapi.jenkins import Jenkins
from blinkstick import blinkstick

led = blinkstick.find_first()
current_time = lambda: int(time.time())
# led.set_mode(0)
found_running_job = False
thread_status_stop = thread_status = None


def get_server_instance():
    jenkins_url = 'http://jenkins'
    return Jenkins(jenkins_url)


def log(message):
    print "%s: %s" % (time.ctime(), message)


def signal_handler():
    log("Will exit")
    led.turn_off()
    if thread_status and thread_status.isAlive():
        thread_status_stop.set()
        thread_status.join()
    sys.exit(0)


def get_jobs(regex):
    p = re.compile(regex, re.IGNORECASE)
    filtered_jobs = []
    j = get_server_instance()
    jobs_list = j.get_jobs_list()
    for job_name in jobs_list:
        if p.match(job_name):
            job = j.get_job(job_name)
            filtered_jobs.append(job)
    return filtered_jobs


def get_running_job(jobs):
    for job in jobs:
        if job.is_running():
            return job
    return None


def get_queued_job(jobs):
    for job in jobs:
        if job.is_queued():
            return job
    return None


def running(name):
    log("Started job %s" % name)
    led.set_color(name='blue')


def show_status(status, stop_event):
    # log("Start status: %s" % status)
    led.blink(name='blue', repeats=5, delay=300)
    led.turn_off()
    time.sleep(1.0)
    color = 'green' if status == 'SUCCESS' else 'red'
    led.set_color(name=color)
    # end_time = current_time() + 600
    #    and current_time() < end_time
    while not stop_event.is_set():
        time.sleep(10.0)
    # log("End status: %s" % status)
    # led.turn_off()


def run_check(regex):
    global found_running_job, thread_status, thread_status_stop
    # log("run_check")
    jobs = get_jobs(regex)
    # log("Got jobs: %s" % jobs)
    running_job = get_running_job(jobs)
    queued_job = get_queued_job(jobs)

    if running_job or queued_job:
        if thread_status and thread_status.isAlive():
            thread_status_stop.set()
            thread_status.join()

    if running_job:
        if (not found_running_job or (found_running_job and found_running_job.name != running_job.name)):
            found_running_job = running_job
            if thread_status and thread_status.isAlive():
                thread_status_stop.set()
                thread_status.join()
            running(running_job.name)
        time.sleep(3.0)
    elif found_running_job:
        last_build = found_running_job.get_last_build()
        status = last_build.get_status()
        log("Build %s #%s, status: %s" % (found_running_job.name,
            last_build.get_number(), status))
        found_running_job = False

        thread_status_stop = Event()
        thread_status = Thread(target=show_status, args=(status, thread_status_stop))
        thread_status.start()
        time.sleep(60.0)
    elif queued_job:
        found_running_job = False
        time.sleep(3.0)
    else:
        time.sleep(60.0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    led.turn_off()
    while True:
        run_check(sys.argv[1])
