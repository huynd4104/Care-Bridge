package db.migration;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.zip.GZIPInputStream;

import org.flywaydb.core.api.migration.BaseJavaMigration;
import org.flywaydb.core.api.migration.Context;
import org.postgresql.PGConnection;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Seeds the AI RAG knowledge base (public.maternal_knowledge_chunks, created by V3) from a
 * pre-chunked, pre-embedded snapshot so a fresh database does not need to re-run chunking or
 * call the embedding API.
 *
 * <p>Snapshot: {@code db/data_seed/maternal_knowledge_chunks.csv.gz} — 54,238 rows exported with
 * {@code COPY (SELECT id, title, stage, topic, source, section, content, chunk_index, embedding,
 * created_at FROM public.maternal_knowledge_chunks ORDER BY id) TO STDOUT WITH (FORMAT csv)}.
 * Embeddings are 768-dim vectors produced by the CareBridgeAITriageService Gemini embedder
 * ({@code GEMINI_EMBEDDING_MODEL}); regenerate the snapshot if the embedding model or dimension
 * changes, otherwise query vectors and stored vectors will not be comparable.
 *
 * <p>The load is skipped when the table already has rows (e.g. the AI service already ingested documents), so
 * existing databases are never overwritten or duplicated.
 */
public class V16__seed_maternal_knowledge_chunks extends BaseJavaMigration {

    private static final Logger log = LoggerFactory.getLogger(V16__seed_maternal_knowledge_chunks.class);

    private static final String SNAPSHOT_RESOURCE = "db/data_seed/maternal_knowledge_chunks.csv.gz";

    private static final String COPY_SQL = """
            COPY public.maternal_knowledge_chunks
                (id, title, stage, topic, source, section, content, chunk_index, embedding, created_at)
            FROM STDIN WITH (FORMAT csv)
            """;

    @Override
    public void migrate(Context context) throws Exception {
        Connection connection = context.getConnection();

        if (!tableExists(connection)) {
            log.warn("V16: public.maternal_knowledge_chunks does not exist; skipping knowledge snapshot seed");
            return;
        }

        // Align V3's varchar limits with the AI service model (app/models/db_models.py uses TEXT):
        // ingested topic/source values exceed varchar(100)/varchar(255). varchar -> text is a
        // metadata-only change in PostgreSQL and a no-op on databases the AI service created.
        try (Statement statement = connection.createStatement()) {
            statement.execute("""
                    ALTER TABLE public.maternal_knowledge_chunks
                        ALTER COLUMN title TYPE text,
                        ALTER COLUMN stage TYPE text,
                        ALTER COLUMN topic TYPE text,
                        ALTER COLUMN source TYPE text,
                        ALTER COLUMN section TYPE text
                    """);
        }

        if (hasRows(connection)) {
            log.info("V16: public.maternal_knowledge_chunks already has data; skipping knowledge snapshot seed");
            return;
        }

        try (Statement statement = connection.createStatement()) {
            // Building the HNSW index once after the load is far faster than maintaining it per row.
            statement.execute("SET LOCAL maintenance_work_mem = '512MB'");
            statement.execute("DROP INDEX IF EXISTS public.idx_maternal_chunks_embedding_hnsw");

            long rows;
            try (InputStream snapshot = openSnapshot()) {
                rows = connection.unwrap(PGConnection.class).getCopyAPI().copyIn(COPY_SQL, snapshot);
            }

            statement.execute("""
                    SELECT setval(pg_get_serial_sequence('public.maternal_knowledge_chunks', 'id'),
                                  COALESCE((SELECT MAX(id) FROM public.maternal_knowledge_chunks), 1))
                    """);
            // Same definition as V3.
            statement.execute("""
                    CREATE INDEX IF NOT EXISTS idx_maternal_chunks_embedding_hnsw
                    ON public.maternal_knowledge_chunks
                    USING hnsw (embedding vector_cosine_ops)
                    """);

            log.info("V16: seeded {} maternal knowledge chunks from {}", rows, SNAPSHOT_RESOURCE);
        }
    }

    private static InputStream openSnapshot() throws Exception {
        InputStream resource = V16__seed_maternal_knowledge_chunks.class.getClassLoader()
                .getResourceAsStream(SNAPSHOT_RESOURCE);
        if (resource == null) {
            throw new IllegalStateException("Missing classpath resource " + SNAPSHOT_RESOURCE);
        }
        return new GZIPInputStream(new BufferedInputStream(resource), 64 * 1024);
    }

    private static boolean tableExists(Connection connection) throws Exception {
        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(
                     "SELECT to_regclass('public.maternal_knowledge_chunks') IS NOT NULL")) {
            return rs.next() && rs.getBoolean(1);
        }
    }

    private static boolean hasRows(Connection connection) throws Exception {
        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(
                     "SELECT EXISTS (SELECT 1 FROM public.maternal_knowledge_chunks)")) {
            return rs.next() && rs.getBoolean(1);
        }
    }
}
