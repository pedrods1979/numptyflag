from numpty_flag.ringbuffer import RingBuffer


def test_prunes_samples_older_than_max_age():
    rb = RingBuffer(max_age_seconds=10)
    rb.append(0.0, "a")
    rb.append(5.0, "b")
    rb.append(11.0, "c")  # cutoff is 1.0, so "a" at t=0 should be pruned
    assert len(rb) == 2
    assert rb.oldest() == (5.0, "b")


def test_value_at_or_before_returns_last_sample_not_after_timestamp():
    rb = RingBuffer(max_age_seconds=100)
    rb.append(0.0, 0)
    rb.append(10.0, 3)
    rb.append(20.0, 8)

    assert rb.value_at_or_before(15.0) == 3
    assert rb.value_at_or_before(20.0) == 8
    assert rb.value_at_or_before(-1.0, default="none") == "none"


def test_empty_buffer_has_no_oldest_or_newest():
    rb = RingBuffer(max_age_seconds=10)
    assert rb.oldest() is None
    assert rb.newest() is None
    assert len(rb) == 0
