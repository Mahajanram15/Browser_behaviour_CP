import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { HeroBanner } from './components/HeroBanner';
import { CourseCard } from './components/CourseCard';
import { StatsGrid } from './components/StatsGrid';
import { LearningChart } from './components/LearningChart';
import { PromoCard } from './components/PromoCard';
import { CourseDetailModal } from './components/CourseDetailModal';
import { LessonPlayerView } from './components/LessonPlayerView';
import { SessionAnalysisModal } from './components/SessionAnalysisModal';
import { CourseItem, LearnerProgressState, QuizAttempt, RiskResponse, ExplanationResponse } from '../../types';
import { AppApiClient, apiClient } from '../../services/api';
import { BehavioralSDK, TelemetryStats } from '@behavioral-integrity/sdk';
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  BookOpen,
  Radio,
  Square,
  Bot,
  User,
  RefreshCw,
  Cpu,
} from 'lucide-react';

interface LearnSphereLandingPageProps {
  appClient: AppApiClient;
  sdk?: BehavioralSDK;
  stats?: TelemetryStats;
  onRefreshStats?: () => void;
  onRefreshDashboardStats?: () => Promise<void> | void;
  onExploreCatalog?: () => void;
  onNavigateToMatrix?: () => void;
}

export const LearnSphereLandingPage: React.FC<LearnSphereLandingPageProps> = ({
  appClient,
  sdk,
  stats,
  onRefreshStats,
  onRefreshDashboardStats,
  onExploreCatalog: _onExploreCatalog,
  onNavigateToMatrix,
}) => {
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('All');
  const [selectedCourse, setSelectedCourse] = useState<CourseItem | null>(null);
  const [selectedSidebarTab, setSelectedSidebarTab] = useState<string>('home');

  // Lesson player view & session-local progress state
  const [activeView, setActiveView] = useState<'catalog' | 'player'>('catalog');
  const [playerCourse, setPlayerCourse] = useState<CourseItem | null>(null);
  const [playerLessonId, setPlayerLessonId] = useState<string | undefined>(undefined);
  const [learnerProgress, setLearnerProgress] = useState<LearnerProgressState>({});

  // Carousel page state for Popular Courses section
  const [popularCarouselIndex, setPopularCarouselIndex] = useState<number>(0);

  // Stage 4: Session Controller & Verification Analysis State
  const [analysisModalOpen, setAnalysisModalOpen] = useState<boolean>(false);
  const [analyzedSessionId, setAnalyzedSessionId] = useState<string>('');
  const [analyzedScenarioType, setAnalyzedScenarioType] = useState<'manual' | 'synthetic_automation'>('manual');
  const [analyzedEventCount, setAnalyzedEventCount] = useState<number>(0);
  const [analyzedRiskData, setAnalyzedRiskData] = useState<RiskResponse | null>(null);
  const [analyzedExplanationData, setAnalyzedExplanationData] = useState<ExplanationResponse | null>(null);
  const [sessionActionLoading, setSessionActionLoading] = useState<boolean>(false);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);

  const coursesSectionRef = useRef<HTMLDivElement>(null);

  // Fetch courses with current filters
  const loadCourses = async (query = '', category = 'All', difficulty = 'All') => {
    setLoading(true);
    try {
      if (query.trim()) {
        const res = await appClient.searchCourses(query.trim(), 10);
        if (res.data) {
          setCourses(res.data.results);
        }
      } else {
        const params: Record<string, any> = { page: 1, page_size: 20 };
        if (category !== 'All') params.category = category;
        if (difficulty !== 'All') params.difficulty = difficulty;

        const res = await appClient.getCourses(params);
        if (res.data) {
          setCourses(res.data.courses);
        }
      }
    } catch (err) {
      console.error('Failed to load courses:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCourses(searchQuery, selectedCategory, selectedDifficulty);
  }, [selectedCategory, selectedDifficulty]);

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) {
      loadCourses('', selectedCategory, selectedDifficulty);
    }
  };

  const handleSearchSubmit = () => {
    loadCourses(searchQuery, selectedCategory, selectedDifficulty);
  };

  // Divide courses between "My Courses" (2 items) and "Popular Courses" (remaining items)
  const myCourses = useMemo(() => {
    if (courses.length <= 2) return courses;
    return courses.slice(0, 2);
  }, [courses]);

  const popularCoursesPool = useMemo(() => {
    if (courses.length <= 2) return [];
    return courses.slice(2);
  }, [courses]);

  // Display 3 cards per view for popular courses
  const visiblePopularCourses = useMemo(() => {
    if (popularCoursesPool.length <= 3) return popularCoursesPool;
    const start = (popularCarouselIndex * 3) % popularCoursesPool.length;
    const slice = popularCoursesPool.slice(start, start + 3);
    if (slice.length < 3) {
      return [...slice, ...popularCoursesPool.slice(0, 3 - slice.length)];
    }
    return slice;
  }, [popularCoursesPool, popularCarouselIndex]);

  const handleNextPopular = () => {
    if (popularCoursesPool.length <= 3) return;
    setPopularCarouselIndex((prev) => prev + 1);
  };

  const handlePrevPopular = () => {
    if (popularCoursesPool.length <= 3) return;
    setPopularCarouselIndex((prev) => (prev > 0 ? prev - 1 : Math.ceil(popularCoursesPool.length / 3) - 1));
  };

  const handleJoinNow = () => {
    coursesSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
    if (courses.length > 0) {
      setSelectedCourse(courses[0]);
    }
  };

  const handleStartLearning = (course: CourseItem, lessonId?: string) => {
    setPlayerCourse(course);
    setPlayerLessonId(lessonId);
    setSelectedCourse(null);
    setActiveView('player');
  };

  const handleBackToCatalog = () => {
    setActiveView('catalog');
    setSelectedSidebarTab('home');
  };

  const handleSidebarNavigate = (tab: string) => {
    setSelectedSidebarTab(tab);
    if (tab === 'home') {
      if (activeView !== 'catalog') {
        setActiveView('catalog');
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
      setSessionNotice(null);
    } else if (tab === 'courses') {
      if (activeView !== 'catalog') {
        setActiveView('catalog');
      }
      coursesSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
      setSessionNotice(null);
    } else {
      const labels: Record<string, string> = {
        calendar: 'Schedule',
        assessments: 'Achievements',
        community: 'Community',
        messages: 'Messages',
        settings: 'Settings',
      };
      const moduleName = labels[tab] || tab;
      setSessionNotice(`LearnSphere Demo Notice: The "${moduleName}" module is not implemented yet. It serves as an illustrative LMS section for behavioral telemetry.`);
    }
  };

  const handleToggleCompleteLesson = (courseId: string, lessonId: string) => {
    setLearnerProgress((prev) => {
      const currentRecord = prev[courseId] || { completedLessonIds: [], quizAttempts: {} };
      const isCompleted = currentRecord.completedLessonIds.includes(lessonId);
      const updatedCompletedIds = isCompleted
        ? currentRecord.completedLessonIds.filter((id) => id !== lessonId)
        : [...currentRecord.completedLessonIds, lessonId];

      return {
        ...prev,
        [courseId]: {
          ...currentRecord,
          completedLessonIds: updatedCompletedIds,
        },
      };
    });
  };

  const handleRecordQuizAttempt = (courseId: string, attempt: QuizAttempt) => {
    setLearnerProgress((prev) => {
      const currentRecord = prev[courseId] || { completedLessonIds: [], quizAttempts: {} };
      return {
        ...prev,
        [courseId]: {
          ...currentRecord,
          quizAttempts: {
            ...currentRecord.quizAttempts,
            [attempt.lessonId]: attempt,
          },
        },
      };
    });
  };

  const handleStartManualSession = async () => {
    if (!sdk) return;
    setSessionActionLoading(true);
    setSessionNotice(null);
    try {
      await sdk.start({
        collectionMode: 'HUMAN',
        taskId: 'TASK_LEARN_MANUAL',
      });
      const sId = sdk.getSessionId();
      if (!sId) {
        throw new Error('SDK failed to initialize or bind a session ID for manual session.');
      }
      onRefreshStats?.();
      setSessionNotice(`Manual session active (${sId.substring(0, 16)}...). Telemetry is capturing as you learn.`);
    } catch (err: any) {
      console.error('Failed to start manual session:', err);
      setSessionNotice(`Error starting session: ${err?.message || err}`);
    } finally {
      setSessionActionLoading(false);
    }
  };

  const handleEndSessionAndInspect = async (intendedScenario: 'manual' | 'synthetic_automation' = 'manual') => {
    if (!sdk) return;
    const currentId = stats?.sessionId;
    if (!currentId) return;

    setSessionActionLoading(true);
    setSessionNotice('Ending session, computing behavioral feature vector & evaluating active model inference...');
    try {
      await sdk.flush();
      const endRes = await sdk.stop(intendedScenario === 'synthetic_automation' ? 'AUTOMATED_SIMULATION_COMPLETED' : 'MANUAL_SESSION_COMPLETED');
      onRefreshStats?.();

      const [riskRes, explRes] = await Promise.all([
        apiClient.getRiskScore(currentId),
        apiClient.getExplanation(currentId),
      ]);

      setAnalyzedSessionId(currentId);
      setAnalyzedScenarioType(intendedScenario);
      setAnalyzedEventCount(endRes?.total_events_captured ?? stats?.eventsSent ?? 0);
      setAnalyzedRiskData(riskRes);
      setAnalyzedExplanationData(explRes);
      setAnalysisModalOpen(true);
      setSessionNotice(null);

      try {
        await onRefreshDashboardStats?.();
      } catch (statsErr) {
        console.error('Failed to refresh dashboard stats after session completion:', statsErr);
      }
    } catch (err: any) {
      console.error('Failed to evaluate session:', err);
      setSessionNotice(`Failed to evaluate session: ${err?.message || err}`);
    } finally {
      setSessionActionLoading(false);
    }
  };

  const handleRunSyntheticBotSimulation = async () => {
    if (!sdk) return;
    setSessionActionLoading(true);
    setSessionNotice('Running controlled synthetic bot simulation against LearnSphere...');
    try {
      await sdk.start({
        collectionMode: 'AUTOMATED',
        automationCondition: 'AUTOMATED_DETERMINISTIC',
        taskId: 'TASK_LEARN_AUTOMATION',
        label: 1,
        syntheticOnly: true,
      });
      const boundSessionId = sdk.getSessionId();
      if (!boundSessionId) {
        throw new Error('SDK failed to initialize or bind a session ID for synthetic simulation.');
      }
      onRefreshStats?.();

      const baseT = Date.now();

      // Deterministic linear mouse telemetry (constant velocity, zero curvature)
      for (let i = 0; i < 16; i++) {
        sdk.recordEvent({
          event_type: 'mouse_move',
          client_timestamp: baseT + i * 33,
          event_data: {
            x: 120 + i * 25,
            y: 180 + i * 20,
            distance_px: 32.0,
            time_delta_ms: 33,
            velocity_px_s: 960.0,
            acceleration_px_s2: 0.0,
            angle_degrees: 38.6,
            direction_change_deg: 0.0,
          },
        });
      }

      // Robotic click
      sdk.recordEvent({
        event_type: 'mouse_click',
        client_timestamp: baseT + 580,
        event_data: {
          x: 450,
          y: 320,
          button: 0,
          click_type: 'single',
          time_since_last_click_ms: 550,
          target_category: 'button',
        },
      });

      // Robotic keystroke intervals (constant 70ms dwell, 50ms flight, 0 variance)
      for (let k = 0; k < 6; k++) {
        sdk.recordEvent({
          event_type: 'key_meta',
          client_timestamp: baseT + 750 + k * 120,
          event_data: {
            dwell_ms: 70,
            flight_ms: 50,
            inter_key_interval_ms: 120,
            is_backspace: false,
            is_paste: false,
          },
        });
      }

      // Robotic scroll burst
      sdk.recordEvent({
        event_type: 'scroll',
        client_timestamp: baseT + 1550,
        event_data: {
          scroll_x: 0,
          scroll_y: 220,
          delta_x: 0,
          delta_y: 220,
          velocity_px_s: 1500.0,
          direction: 'down',
          time_since_last_scroll_ms: 100,
        },
      });

      // Navigation & API access
      sdk.recordEvent({
        event_type: 'navigation',
        client_timestamp: baseT + 1800,
        event_data: {
          path: '/api/courses/details?course_id=course_cs101',
          referrer: '/api/courses',
          dwell_time_ms: 1800,
          sequence_number: 2,
        },
      });

      // Instrumented domain API access
      await appClient.getCourses({ page: 1, page_size: 10 });
      await appClient.getCourseDetails('course_cs101');

      // Flush buffer and finalize session
      await sdk.flush();
      const endRes = await sdk.stop('AUTOMATED_DETERMINISTIC_SIMULATION_COMPLETED');
      onRefreshStats?.();

      const [riskRes, explRes] = await Promise.all([
        apiClient.getRiskScore(boundSessionId),
        apiClient.getExplanation(boundSessionId),
      ]);

      setAnalyzedSessionId(boundSessionId);
      setAnalyzedScenarioType('synthetic_automation');
      setAnalyzedEventCount(endRes?.total_events_captured ?? 25);
      setAnalyzedRiskData(riskRes);
      setAnalyzedExplanationData(explRes);
      setAnalysisModalOpen(true);
      setSessionNotice(null);

      try {
        await onRefreshDashboardStats?.();
      } catch (statsErr) {
        console.error('Failed to refresh dashboard stats after simulation completion:', statsErr);
      }
    } catch (err: any) {
      console.error('Synthetic simulation failed:', err);
      setSessionNotice(`Synthetic simulation error: ${err?.message || err}`);
    } finally {
      setSessionActionLoading(false);
    }
  };

  if (activeView === 'player' && playerCourse) {
    return (
      <>
        <LessonPlayerView
          course={playerCourse}
          initialLessonId={playerLessonId}
          appClient={appClient}
          progressRecord={learnerProgress[playerCourse.id]}
          onToggleCompleteLesson={handleToggleCompleteLesson}
          onRecordQuizAttempt={handleRecordQuizAttempt}
          onBackToCatalog={handleBackToCatalog}
          onOpenCourseDetails={() => setSelectedCourse(playerCourse)}
        />
        {selectedCourse && (
          <CourseDetailModal
            course={selectedCourse}
            onClose={() => setSelectedCourse(null)}
            appClient={appClient}
            onStartLearning={handleStartLearning}
          />
        )}
        <SessionAnalysisModal
          isOpen={analysisModalOpen}
          onClose={() => setAnalysisModalOpen(false)}
          scenarioType={analyzedScenarioType}
          sessionId={analyzedSessionId}
          totalEvents={analyzedEventCount}
          riskData={analyzedRiskData}
          explanationData={analyzedExplanationData}
          onNavigateToMatrix={onNavigateToMatrix}
        />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-[#ECEAF6] p-2.5 sm:p-5 lg:p-7 relative overflow-x-hidden flex justify-center items-start font-sans">
      {/* Decorative Organic Curved Gradients in Background */}
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-purple-300/35 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 -right-32 w-[30rem] h-[30rem] bg-indigo-300/30 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 left-1/4 w-80 h-80 bg-purple-200/40 rounded-full blur-3xl pointer-events-none" />

      {/* Main Centered Rounded Dashboard Surface */}
      <div className="max-w-[1400px] w-full bg-[#FAFAFE] rounded-[36px] shadow-[0_20px_60px_-15px_rgba(79,70,229,0.07)] border border-white/80 p-3.5 sm:p-6 lg:p-7 flex flex-col md:flex-row gap-5 lg:gap-6 relative z-10">
        {/* Left Floating Sidebar */}
        <Sidebar activeTab={selectedSidebarTab} onNavigate={handleSidebarNavigate} />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col space-y-5 overflow-hidden min-w-0">
          {/* Stage 4: Live Telemetry Session Controller Bar */}
          <div className="bg-white/95 rounded-2xl border border-purple-200/90 shadow-sm p-3.5 px-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center border border-purple-100 shrink-0">
                <Radio className={`w-4 h-4 ${stats?.isRunning ? 'text-emerald-600 animate-pulse' : 'text-slate-400'}`} />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-slate-800">
                    CrossTrace Live Session Controller
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.2 rounded-full uppercase font-bold ${
                      stats?.isRunning
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {stats?.isRunning ? 'Streaming Active' : 'Idle'}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                  {stats?.isRunning ? (
                    <>Session: <span className="text-purple-700 font-bold">{stats.sessionId?.substring(0, 18)}...</span> • Events Sent: <span className="font-bold text-slate-800">{stats.eventsSent}</span></>
                  ) : (
                    'Evaluate human operator vs. synthetic bot behaviors against LearnSphere.'
                  )}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              {!stats?.isRunning ? (
                <>
                  <button
                    onClick={handleStartManualSession}
                    disabled={sessionActionLoading}
                    className="px-3.5 py-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-800 text-xs font-bold border border-slate-200 shadow-sm transition-all flex items-center space-x-1.5 cursor-pointer disabled:opacity-40"
                  >
                    <User className="w-3.5 h-3.5 text-purple-600" />
                    <span>Start Manual Session</span>
                  </button>
                  <button
                    onClick={handleRunSyntheticBotSimulation}
                    disabled={sessionActionLoading}
                    className="px-3.5 py-1.5 rounded-xl bg-[#6941C6] hover:bg-[#53389E] text-white text-xs font-bold shadow-md shadow-purple-600/20 transition-all flex items-center space-x-1.5 cursor-pointer disabled:opacity-40"
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>Run Synthetic Bot Simulation</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => sdk?.flush()}
                    title="Force Flush Buffer"
                    className="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-all cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleEndSessionAndInspect('manual')}
                    disabled={sessionActionLoading}
                    className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md transition-all flex items-center space-x-1.5 cursor-pointer disabled:opacity-40"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    <span>End Session &amp; Analyze</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {sessionNotice && (
            <div className="p-3 bg-purple-50 border border-purple-200 rounded-xl text-purple-800 text-xs flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-purple-600 shrink-0" />
              <span>{sessionNotice}</span>
            </div>
          )}

          {/* Top Search & Profile Area */}
          <TopHeader
            searchQuery={searchQuery}
            onSearchChange={handleSearchChange}
            onSearchSubmit={handleSearchSubmit}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            selectedDifficulty={selectedDifficulty}
            onSelectDifficulty={setSelectedDifficulty}
          />

          {/* Two-Column Dashboard Content */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left / Main Column (8 cols ~ 67%) */}
            <div className="lg:col-span-8 flex flex-col space-y-6 min-w-0">
              {/* Purple Hero Banner */}
              <HeroBanner onJoinNowClick={handleJoinNow} />

              {/* My Courses Section */}
              <div ref={coursesSectionRef} className="flex flex-col space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <h2 className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight">
                      My Courses
                    </h2>
                    <span className="text-[11px] font-semibold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full font-mono border border-purple-100">
                      Explore Track
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-medium">
                    {courses.length} courses available
                  </span>
                </div>

                {loading ? (
                  <div className="py-12 bg-white rounded-2xl border border-slate-100 flex flex-col items-center justify-center space-y-2">
                    <Loader2 className="w-6 h-6 text-purple-600 animate-spin" />
                    <span className="text-xs text-slate-400">Loading courses...</span>
                  </div>
                ) : myCourses.length === 0 ? (
                  <div className="p-8 bg-white rounded-2xl border border-slate-100 text-center">
                    <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p className="text-xs text-slate-500 font-medium">No courses matched your search or filters.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {myCourses.map((c) => (
                      <CourseCard key={c.id} course={c} onSelect={setSelectedCourse} />
                    ))}
                  </div>
                )}
              </div>

              {/* Popular Courses Section */}
              <div className="flex flex-col space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <h2 className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight">
                    Popular Courses
                  </h2>

                  {/* Carousel Controls */}
                  {popularCoursesPool.length > 3 && (
                    <div className="flex items-center space-x-1.5">
                      <button
                        onClick={handlePrevPopular}
                        title="Previous Popular Courses"
                        className="w-7 h-7 rounded-full bg-white hover:bg-slate-100 border border-slate-200/80 shadow-sm flex items-center justify-center text-slate-600 transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleNextPopular}
                        title="Next Popular Courses"
                        className="w-7 h-7 rounded-full bg-white hover:bg-slate-100 border border-slate-200/80 shadow-sm flex items-center justify-center text-slate-600 transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>

                {loading ? (
                  <div className="py-8 bg-white rounded-2xl border border-slate-100 flex justify-center">
                    <Loader2 className="w-6 h-6 text-purple-600 animate-spin" />
                  </div>
                ) : visiblePopularCourses.length === 0 ? (
                  <div className="p-6 bg-white rounded-2xl border border-slate-100 text-center text-xs text-slate-500">
                    All available courses are displayed above in Explore Track.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {visiblePopularCourses.map((c) => (
                      <CourseCard key={c.id} course={c} onSelect={setSelectedCourse} compact />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column (4 cols ~ 33%) */}
            <div className="lg:col-span-4 flex flex-col space-y-5 min-w-0">
              {/* Learning Statistics (2x2 Grid) */}
              <StatsGrid />

              {/* Learning Hours / Statistics Chart */}
              <LearningChart />

              {/* Promotional Go Premium Card */}
              <PromoCard />
            </div>
          </div>
        </main>
      </div>

      {/* Course Detail Modal */}
      {selectedCourse && (
        <CourseDetailModal
          course={selectedCourse}
          onClose={() => setSelectedCourse(null)}
          appClient={appClient}
          onStartLearning={handleStartLearning}
        />
      )}

      {/* Stage 4: Session Behavioral & ML Analysis Modal */}
      <SessionAnalysisModal
        isOpen={analysisModalOpen}
        onClose={() => setAnalysisModalOpen(false)}
        scenarioType={analyzedScenarioType}
        sessionId={analyzedSessionId}
        totalEvents={analyzedEventCount}
        riskData={analyzedRiskData}
        explanationData={analyzedExplanationData}
        onNavigateToMatrix={onNavigateToMatrix}
      />
    </div>
  );
};
