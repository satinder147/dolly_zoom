-- Create base tables.

CREATE TABLE request_stats(
        request_id VARCHAR(32),
        video_decoding_time SMALLINT,
        transform_calculation_time SMALLINT,
        video_encoding_time SMALLINT,
        total_time SMALLINT,
        video_width SMALLINT,
        video_height SMALLINT,
        status VARCHAR,
        fps SMALLINT,

        PRIMARY KEY(request_id)
);
