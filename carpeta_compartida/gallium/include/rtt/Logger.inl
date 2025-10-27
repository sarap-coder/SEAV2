#ifndef ORO_CORELIB_LOGGER_INL
#define ORO_CORELIB_LOGGER_INL

/**
 * @file Logger.inl
 * Provides empty inlines when no logging is used, which the
 * compiler can optimize out.
 */



namespace RTT
{
    template< class T>
    Logger& Logger::operator<<( const T &t ) {
#ifndef OROBLD_DISABLE_LOGGING
        if ( !mayLog() )
            return *this;

        os::MutexLock lock( inpguard );
        if ( this->mayLogStdOut() )
            logline << t;

#if defined(OROSEM_FILE_LOGGING) || defined(OROSEM_REMOTE_LOGGING)
        // log Info or better to log file, even if not started.
        if ( this->mayLogFile() )
            fileline << t;
#endif
#endif
        return *this;
    }

#ifdef OROBLD_DISABLE_LOGGING

    // instance will be actually null
    inline Logger& Logger::log() {
        return *_instance;
    }

    inline Logger& Logger::log(LogLevel) {
        return *_instance;
    }

    inline bool Logger::mayLog() const {
        return false;
    }

    inline void Logger::mayLogStdOut(bool ) {
    }

    inline void Logger::mayLogFile(bool ) {
    }

    inline void Logger::allowRealTime() {
    }

    inline void Logger::disallowRealTime() {
    }

    inline std::ostream&
    Logger::nl(std::ostream& __os)
    {
        return __os;
    }

    inline std::ostream&
    Logger::endl(std::ostream& __os)
    {
        return __os;
    }

    inline std::ostream&
    Logger::flush(std::ostream& __os)
    {
        return __os;
    }


    inline Logger::In::In(const std::string&)
    {
    }

    inline Logger::In::~In()
    {
    }

    inline Logger& Logger::in(const std::string&)
    {
        return *this;
    }

    inline Logger& Logger::out(const std::string&)
    {
        return *this;
    }

    inline std::string Logger::getLogModule() const {
        return "";
    }

    inline void Logger::startup() {
    }

    inline void Logger::shutdown() {
    }

    inline std::string Logger::getLogLine() {
        return "";
    }

    inline void Logger::setStdStream( std::ostream& ) {
    }

    inline Logger& Logger::operator<<( const std::string& ) {
        return *this;
    }

    inline Logger& Logger::operator<<(LogLevel) {
        return *this;
    }

    inline Logger& Logger::operator<<(std::ostream& (*pf)(std::ostream&))
    {
        return *this;
    }

    inline void Logger::logflush() {
     }

    inline void Logger::lognl() {
     }

    inline void Logger::logendl() {
     }

    inline void Logger::setLogLevel( LogLevel ) {
    }

    inline Logger::LogLevel Logger::getLogLevel() const {
        return Never;
    }
#endif

}

#endif
